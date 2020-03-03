# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from sqlalchemy.exc import SQLAlchemyError
from forms import *
from flask_migrate import Migrate

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#


app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    image_link = db.Column(db.String(500))
    website_link = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False, server_default="false")
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='venue', cascade='all,delete', lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    image_link = db.Column(db.String(500))
    website_link = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime())
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)

    def for_render(self):
        return {
            "artist_id": self.artist_id,
            "venue_id": self.venue_id,
            "start_time": str(self.date)
        }

    def with_artist_and_venue(self):
        with_artist = self.for_render()
        with_artist["venue_name"] = self.venue.name
        with_artist["venue_image_link"] = self.venue.image_link
        with_artist["artist_name"] = self.artist.name
        with_artist['artist_image_link'] = self.artist.image_link

        return with_artist


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = Venue.query.distinct('state', 'city').order_by('state').all()
    for place in data:
        place.venues = Venue.query.filter_by(state=place.state, city=place.city)
    return render_template('pages/venues.html', areas=data);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term')
    data = search_results(search_term, Venue)
    return render_template('pages/search_venues.html', results=data, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = Venue.query.filter(Venue.id == venue_id).one()
    split_upcoming_past_shows(data)
    return render_template('pages/show_venue.html', venue=data)


def split_upcoming_past_shows(data):
    data.past_shows_count = 0
    data.upcoming_shows_count = 0
    data.past_shows = []
    data.upcoming_shows = []
    for it_show in data.shows:
        if it_show.date < datetime.now():
            data.past_shows.append(it_show.with_artist_and_venue())
            data.past_shows_count += 1
        else:
            data.upcoming_shows.append(it_show.with_artist_and_venue())
            data.upcoming_shows_count += 1


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    venue = Venue()
    venue_values(venue)
    form = VenueForm(request.form)
    try:
        if request.method == 'POST' and form.validate():
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + request.form['name'] + ' was successfully listed!')
            return redirect(url_for('venues'))
        else:
            print(form.errors)
    except SQLAlchemyError as e:
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.')

        # on successful db insert, flash success
    return render_template('pages/home.html', form=form)


@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        return redirect(url_for('venues'))
    except SQLAlchemyError as e:
        print(e)
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.order_by('id').all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term')
    data = search_results(search_term, Artist)
    return render_template('pages/search_artists.html', results=data,
                           search_term=request.form.get('search_term', ''))


def search_results(search_term, db_object):
    results_data = db_object.query.filter(db_object.name.ilike('%' + search_term + '%')).all()
    for obj in results_data:
        split_upcoming_past_shows(obj)
    data = {"count": len(results_data), "data": results_data}
    return data


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = Artist.query.filter_by(id=artist_id).one()
    split_upcoming_past_shows(data)
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.filter_by(id=artist_id).one()
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # artist record with ID <artist_id> using the new attributes
    artist_data = Artist.query.filter_by(id=artist_id).one()

    artist_data.name = request.form['name']
    artist_values(artist_data)
    form = ArtistForm(request.form)
    try:
        if request.method == 'POST' and form.validate():
            db.session.commit()
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
        else:
            print(form.errors)
    except SQLAlchemyError as e:
        print(e)
        flash('An error occurred. Artist ' + artist_data.name + ' could not be listed.')

    return redirect(url_for('show_artist', artist_id=artist_id))


def artist_values(artist_data):
    artist_data.name = request.form['name']
    artist_data.city = request.form['city']
    artist_data.state = request.form['state']
    artist_data.phone = request.form['phone']
    artist_data.facebook_link = request.form['facebook_link']
    artist_data.genres = request.form.getlist('genres') or []
    artist_data.image_link = request.form['image_link']
    artist_data.seeking_description = request.form['seeking_description']
    artist_data.seeking_venue = bool(eval(request.form['seeking_venue']))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.filter_by(id=venue_id).one()
    # TODO: populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # venue record with ID <venue_id> using the new attributes
    venue_data = Venue.query.filter_by(id=venue_id).one()
    venue_values(venue_data)
    form = VenueForm(request.form)
    try:
        if request.method == 'POST' and form.validate():
            db.session.commit()
            flash('Venue ' + request.form['name'] + ' was successfully edited!')
        else:
            print(form.errors)
    except SQLAlchemyError as e:
        flash('An error occurred. Venue ' + venue_data.name + ' could not be edited.')

    return redirect(url_for('show_venue', venue_id=venue_id))


def venue_values(venue_data):
    venue_data.name = request.form['name']
    venue_data.phone = request.form['phone']
    venue_data.address = request.form['address']
    venue_data.state = request.form['state']
    venue_data.genres = request.form.getlist('genres') or []
    venue_data.facebook_link = request.form['facebook_link']
    venue_data.image_link = request.form['image_link']
    venue_data.seeking_description = request.form['seeking_description']
    venue_data.seeking_talent = bool(eval(request.form['seeking_talent']))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    artist = Artist()
    artist_values(artist)
    form = ArtistForm(request.form)
    try:
        if request.method == 'POST' and form.validate():
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
            return redirect(url_for('artists'))
        else:
            print(form.errors)
    except SQLAlchemyError as e:
        print(e)
        flash('An error occurred. Artist ' + artist.name + ' could not be listed.')

    return render_template('pages/home.html', form=form)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    show_results = Show.query.all()
    data = []
    for show in show_results:
        data.append(show.with_artist_and_venue())

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    show = Show()
    show.artist_id = request.form['artist_id']
    show.venue_id = request.form['venue_id']
    show.date = request.form['start_time']
    form = ShowForm(request.form);
    try:
        if request.method == 'POST' and form.validate():
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
            return redirect(url_for('shows'))
    except SQLAlchemyError as e:
        flash('An error occurred. Show could not be listed.')
    return render_template('pages/home.html', form=form)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
