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
@auth.login_required
def home():
    return render_template('home.html')


@app.route('/manage')
@auth.login_required
def manage():
    return render_template('manage.html')


@app.route('/rss/all')
def rss_all():
    return None


@app.route('/rss/<monitoring_id>')
def rss_one(monitoring_id):
    return None


# -----------------------------------------------------------


@auth.get_password
def get_password(username):
    if username in app.config['USER']:
        return app.config['USER'].get(username)

    return None
