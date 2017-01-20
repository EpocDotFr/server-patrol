from flask import Flask, render_template, g
from flask_httpauth import HTTPBasicAuth
import logging
import sys
import sqlite3
import os
import arrow

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['DB_FILE'] = 'storage/data/db.sqlite'

app.jinja_env.globals.update(arrow=arrow)

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
    return render_template('home.html', monitorings=get_monitorings_for_home())


@app.route('/rss/all')
def rss_all():
    return None


@app.route('/rss/<monitoring_id>')
def rss_one(monitoring_id):
    return None


@app.route('/manage-monitorings')
@auth.login_required
def manage_monitorings():
    return render_template('manage-monitorings.html', monitorings=get_monitorings_for_managing())


# -----------------------------------------------------------


def get_monitorings_for_home():
    monitorings = g.db.execute('SELECT id, name, url, check_interval, last_checked_at, last_status_change_at, status, created_at FROM monitorings WHERE is_active = 1').fetchall()

    return _get_list_monitoring(monitorings)


def get_monitorings_for_managing():
    monitorings = g.db.execute('SELECT id, name, is_active, url, http_method, verify_https_cert, check_interval, timeout, recipients FROM monitorings').fetchall()

    return _get_list_monitoring(monitorings)


def _get_list_monitoring(monitorings=[]):
    if not monitorings:
        return []

    monitoring_list = []

    for monitoring in monitorings:
        monitoring_list.append(_get_one_monitoring(monitoring))

    return monitoring_list


def _get_one_monitoring(monitoring=None):
    if not monitoring:
        return None

    monitoring = dict(monitoring)

    for column in ['last_checked_at', 'last_status_change_at', 'created_at']:
        if column in monitoring and monitoring[column] is not None:
            monitoring[column] = arrow.get(monitoring[column])

    return monitoring


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
            g.db.execute('CREATE TABLE monitorings (id INTEGER PRIMARY KEY, name TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 0, url TEXT NOT NULL, http_method TEXT CHECK(http_method IN(\'GET\', \'HEAD\', \'POST\', \'PUT\', \'DELETE\')) NOT NULL DEFAULT \'GET\', verify_https_cert INTEGER NOT NULL DEFAULT 1, check_interval INTEGER NOT NULL DEFAULT 5, timeout INTEGER NOT NULL DEFAULT 10, last_checked_at TEXT DEFAULT NULL, last_status_change_at TEXT DEFAULT NULL, status TEXT CHECK(status IN(\'up\', \'down\', \'unknown\')) NOT NULL DEFAULT \'unknown\', recipients TEXT DEFAULT NULL, created_at TEXT NOT NULL DEFAULT (datetime(\'now\')))')


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()
