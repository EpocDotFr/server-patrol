from flask import Flask, render_template, g
from flask_httpauth import HTTPBasicAuth
import logging
import sys
import sqlite3
import os

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['DB_FILE'] = 'storage/data/db.sqlite'

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


@app.before_request
def connect_to_db():
    if not hasattr(g, 'db'):
        db_is_new = not os.path.isfile(app.config['DB_FILE'])

        g.db = sqlite3.connect(app.config['DB_FILE'])
        g.db.row_factory = sqlite3.Row

        if db_is_new:
            g.db.execute('CREATE TABLE monitorings (id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, http_method TEXT CHECK(http_method IN(\'GET\', \'HEAD\', \'POST\', \'PUT\', \'DELETE\')) NOT NULL DEFAULT \'GET\', verify_https_cert INTEGER NOT NULL DEFAULT 1, check_interval INTEGER NOT NULL DEFAULT 5, timeout INTEGER NOT NULL DEFAULT 10, last_checked_at TEXT DEFAULT NULL, last_status_change_at TEXT DEFAULT NULL, status TEXT CHECK(status IN(\'up\', \'down\', \'unknown\')) NOT NULL DEFAULT \'unknown\', recipients TEXT DEFAULT NULL)')


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()
