from flask import Flask, render_template
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException
from sqlalchemy_utils import ArrowType
from enum import Enum
import logging
import sys
import os
import arrow


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.jinja_env.globals.update(arrow=arrow)

auth = HTTPBasicAuth()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    stream=sys.stdout
)

logging.getLogger().setLevel(logging.INFO)


# -----------------------------------------------------------
# Routes


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
# Models


class MonitoringHttpMethod(Enum):
    GET = 'GET'
    HEAD = 'HEAD'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'


class MonitoringStatus(Enum):
    UNKNOWN = 'UNKNOWN'
    UP = 'UP'
    DOWN = 'DOWN'


class Monitoring(db.Model):
    __tablename__ = 'monitorings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    http_method = db.Column(db.Enum(MonitoringHttpMethod), default=MonitoringHttpMethod.GET, nullable=False)
    verify_https_cert = db.Column(db.Boolean, default=True, nullable=False)
    check_interval = db.Column(db.Integer, default=5, nullable=False)
    timeout = db.Column(db.Integer, default=10, nullable=False)
    last_checked_at = db.Column(ArrowType, default=None)
    last_status_change_at = db.Column(ArrowType, default=None)
    status = db.Column(db.Enum(MonitoringStatus), default=MonitoringStatus.UNKNOWN, nullable=False)
    last_down_reason = db.Column(db.Text, default=None)
    recipients = db.Column(db.Text, default=None)
    created_at = db.Column(ArrowType, nullable=False)

    def __init__(self, name, is_active, is_public, url, http_method, verify_https_cert, check_interval, timeout, last_checked_at, last_status_change_at, status, last_down_reason, recipients, created_at):
        self.name = name
        self.is_active = is_active
        self.is_public = is_public
        self.url = url
        self.http_method = http_method
        self.verify_https_cert = verify_https_cert
        self.check_interval = check_interval
        self.timeout = timeout
        self.last_checked_at = last_checked_at
        self.last_status_change_at = last_status_change_at
        self.status = status
        self.last_down_reason = last_down_reason
        self.recipients = recipients
        self.created_at = created_at

    def __repr__(self):
        return '<Monitoring> #{} : {}'.format(self.id, self.name)


def get_monitorings_for_home():
    q = Monitoring.query.order_by(Monitoring.name.desc())

    q = q.filter(Monitoring.is_active == True)

    if not auth.username():
        q = q.filter(Monitoring.is_public == True)

    return q.all()


def get_monitorings_for_managing():
    q = Monitoring.query.order_by(Monitoring.name.desc())

    return q.all()


# -----------------------------------------------------------
# CLI commands


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""
    db.drop_all()
    db.create_all()


# -----------------------------------------------------------
# Hooks


@auth.get_password
def get_password(username):
    if username in app.config['USERS']:
        return app.config['USERS'].get(username)

    return None


# -----------------------------------------------------------
# HTTP errors handler


@auth.error_handler
def auth_error():
    return http_error_handler(403, without_code=True)


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(503)
def http_error_handler(error, without_code=False):
    if isinstance(error, HTTPException):
        error = error.code
    else:
        error = 500


    ret = (render_template('errors/{}.html'.format(error)),)

    if not without_code:
        ret = ret + (error,)

    return ret
