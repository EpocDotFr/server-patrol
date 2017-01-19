from flask import Flask, render_template
from flask_httpauth import HTTPBasicAuth
import logging
import sys

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

auth = HTTPBasicAuth()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    stream=sys.stdout
)

logging.getLogger().setLevel(logging.INFO)

# -----------------------------------------------------------


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/rss/all')
def rss_all():
    return None


@app.route('/rss/<monitoring_id>')
def rss_one(monitoring_id):
    return None


@app.route('/manage-monitorings')
@auth.login_required
def manage_monitorings():
    return render_template('manage-monitorings.html')


# -----------------------------------------------------------


@auth.get_password
def get_password(username):
    if username in app.config['USERS']:
        return app.config['USERS'].get(username)

    return None
