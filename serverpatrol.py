from flask import Flask, render_template, redirect, url_for, flash, abort, make_response, Response, g, request
from wtforms import StringField, BooleanField, SelectField, IntegerField, TextAreaField
from flask_babel import Babel, _, lazy_gettext as __, format_datetime
from sqlalchemy_utils import ArrowType
from werkzeug.exceptions import HTTPException
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
import wtforms.validators as validators
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from enum import Enum
import twilio.rest
import PyRSS2Gen
import logging
import requests
import arrow
import json
import click
import time
import sys
import os
import re


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_DEBUG'] = False
app.config['WTF_I18N_ENABLED'] = True

app.config['LANGUAGES'] = {
    'en': 'English',
    'fr': 'Français'
}

app.jinja_env.globals.update(arrow=arrow)

db = SQLAlchemy(app)
babel = Babel(app)
auth = HTTPBasicAuth()
mail = Mail(app)

# Default Python logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    stream=sys.stdout
)

logging.getLogger().setLevel(logging.INFO)

# Default Flask loggers
for handler in app.logger.handlers:
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S'))


# -----------------------------------------------------------
# Routes


@app.route('/')
def home():
    return render_template('home.html', monitorings=Monitoring.query.get_for_home())


@app.route('/admin/')
def admin():
    return render_template('admin/list.html', monitorings=Monitoring.query.get_for_managing())


@app.route('/admin/create', methods=['GET', 'POST'])
@auth.login_required
def admin_create():
    form = MonitoringForm()

    if form.validate_on_submit():
        try:
            monitoring = Monitoring()

            form.populate_obj(monitoring)

            db.session.add(monitoring)
            db.session.commit()

            flash(_('Monitoring created successfuly.'), 'success')

            return redirect(url_for('admin_edit', monitoring_id=monitoring.id))
        except Exception as e:
            flash(_('Error creating this monitoring: %(exception)s', exception=str(e)), 'error')

    return render_template('admin/create.html', form=form)


@app.route('/admin/edit/<monitoring_id>', methods=['GET', 'POST'])
@auth.login_required
def admin_edit(monitoring_id):
    monitoring = Monitoring.query.get(monitoring_id)

    if not monitoring:
        abort(404)

    form = MonitoringForm(obj=monitoring)

    if form.validate_on_submit():
        try:
            form.populate_obj(monitoring)

            db.session.add(monitoring)
            db.session.commit()

            flash(_('Monitoring edited successfuly.'), 'success')

            return redirect(url_for('admin_edit', monitoring_id=monitoring.id))
        except Exception as e:
            flash(_('Error editing this monitoring: %(exception)s', exception=str(e)), 'error')

    return render_template('admin/edit.html', monitoring=monitoring, form=form)


@app.route('/admin/delete/<monitoring_id>')
@auth.login_required
def admin_delete(monitoring_id):
    monitoring = Monitoring.query.get(monitoring_id)

    if not monitoring:
        abort(404)

    try:
        db.session.delete(monitoring)
        db.session.commit()

        flash(_('Monitoring deleted successfuly.'), 'success')
    except Exception as e:
        flash(_('Error deleting this monitoring: %(exception)s', exception=str(e)), 'error')

    return redirect(url_for('admin'))


@app.route('/rss')
def rss():
    monitorings = Monitoring.query.get_for_home()

    rss_items = []

    for monitoring in monitorings:
        title = ''
        description = ''

        if monitoring.status == MonitoringStatus.DOWN:
            title = _('%(monitoring_name)s is down', monitoring_name=monitoring.name)
            description = _('<p><b>%(monitoring_name)s</b> seems to encounter issues and is unreachable since the <b>%(last_status_change)s</b>. The reason is:</p><p>%(last_down_reason)s</p>', monitoring_name=monitoring.name, last_status_change=format_datetime(monitoring.last_status_change_at.datetime, 'short'), last_down_reason=monitoring.last_down_reason)
        elif monitoring.status == MonitoringStatus.UP:
            title = _('%(monitoring_name)s is up', monitoring_name=monitoring.name)
            description = _('<p><b>%(monitoring_name)s</b> is up and reachable since the <b>%(last_status_change)s</b>.</p>', monitoring_name=monitoring.name, last_status_change=format_datetime(monitoring.last_status_change_at.datetime, 'short'))
        elif monitoring.status == MonitoringStatus.UNKNOWN:
            title = _('%(monitoring_name)s status is unknown', monitoring_name=monitoring.name)
            description = _('<p>The status of <b>%(monitoring_name)s</b> is currently unknown.</p>', monitoring_name=monitoring.name)

        rss_items.append(PyRSS2Gen.RSSItem(
            title=title,
            link=monitoring.url,
            description=description,
            guid=PyRSS2Gen.Guid(':'.join([str(monitoring.id), monitoring.status.value, monitoring.last_status_change_at.format()]), isPermaLink=False),
            pubDate=monitoring.last_status_change_at.datetime,
            categories=[monitoring.status.value]
        ))

    rss = PyRSS2Gen.RSS2(
        title=_('Server Patrol - Monitorings status'),
        link=url_for('home', _external=True),
        description=_('Server Patrol - Monitorings status'),
        language=g.CURRENT_LOCALE,
        image=PyRSS2Gen.Image(url_for('static', filename='images/logo.png', _external=True),
                              _('Server Patrol - Monitorings status'),
                              url_for('home', _external=True)),
        lastBuildDate=arrow.now().datetime,
        items=rss_items
    )

    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')


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
    class MonitoringQuery(db.Query):
        def get_for_home(self):
            q = self.order_by(Monitoring.name.asc())

            q = q.filter(Monitoring.is_active == True)

            if auth.username() == '' or auth.username() == None:
                q = q.filter(Monitoring.is_public == True)

            return q.all()

        def get_for_managing(self):
            q = self.order_by(Monitoring.name.asc())

            return q.all()

        def get_for_checking(self):
            q = self.order_by(Monitoring.name.asc())

            q = q.filter(Monitoring.is_active == True)

            return q.all()

    __tablename__ = 'monitorings'
    query_class = MonitoringQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    url = db.Column(db.String(255), nullable=False)
    http_method = db.Column(db.Enum(MonitoringHttpMethod), default=MonitoringHttpMethod.GET)
    _http_headers = db.Column('http_headers', db.Text, default=None)
    http_body_regex = db.Column(db.String(255), default=None)
    verify_https_cert = db.Column(db.Boolean, default=True)
    check_interval = db.Column(db.Integer, default=5)
    timeout = db.Column(db.Integer, default=10)
    last_checked_at = db.Column(ArrowType, default=None)
    last_status_change_at = db.Column(ArrowType, default=None)
    status = db.Column(db.Enum(MonitoringStatus), default=MonitoringStatus.UNKNOWN)
    last_down_reason = db.Column(db.Text, default='')
    _email_recipients = db.Column('email_recipients', db.Text, default=None)
    _sms_recipients = db.Column('sms_recipients', db.Text, default=None)
    created_at = db.Column(ArrowType, default=arrow.now())

    def __init__(self, name=None, url=None, is_active=False, is_public=False, http_method=MonitoringHttpMethod.GET, http_headers='', http_body_regex=None, verify_https_cert=True, check_interval=5, timeout=10, last_checked_at=None, last_status_change_at=None, status=MonitoringStatus.UNKNOWN, last_down_reason='', email_recipients='', sms_recipients='', created_at=arrow.now()):
        self.name = name
        self.url = url
        self.is_active = is_active
        self.is_public = is_public
        self.http_method = http_method
        self.http_headers = http_headers
        self.http_body_regex = http_body_regex
        self.verify_https_cert = verify_https_cert
        self.check_interval = check_interval
        self.timeout = timeout
        self.last_checked_at = last_checked_at
        self.last_status_change_at = last_status_change_at
        self.status = status
        self.last_down_reason = last_down_reason
        self.email_recipients = email_recipients
        self.sms_recipients = sms_recipients
        self.created_at = created_at

    def __repr__(self):
        return '<Monitoring> #{} : {}'.format(self.id, self.name)

    @property
    def next_check(self):
        if self.last_checked_at:
            attr = self.last_checked_at
        else:
            attr = self.created_at

        return attr.floor('minute').replace(minutes=self.check_interval)

    @property
    def status_icon(self):
        if self.status == MonitoringStatus.UP:
            return 'check'
        elif self.status == MonitoringStatus.DOWN:
            return 'times'
        elif self.status == MonitoringStatus.UNKNOWN:
            return 'question'

    @property
    def http_headers(self):
        return json.loads(self._http_headers) if self._http_headers else None

    @http_headers.setter
    def http_headers(self, value):
        if isinstance(value, str):
            self._http_headers = value
        else:
            self._http_headers = json.dumps(value)

    @property
    def email_recipients(self):
        return json.loads(self._email_recipients) if self._email_recipients else None

    @email_recipients.setter
    def email_recipients(self, value):
        if isinstance(value, str):
            self._email_recipients = value
        else:
            self._email_recipients = json.dumps(value)

    @property
    def sms_recipients(self):
        return json.loads(self._sms_recipients) if self._sms_recipients else None

    @sms_recipients.setter
    def sms_recipients(self, value):
        if isinstance(value, str):
            self._sms_recipients = value
        else:
            self._sms_recipients = json.dumps(value)

# -----------------------------------------------------------
# Forms


class MonitoringForm(FlaskForm):
    name = StringField(__('Name'), [validators.DataRequired(), validators.length(max=255)])
    is_active = BooleanField(__('Active?'), default=False)
    is_public = BooleanField(__('Public?'), default=False)
    url = StringField(__('URL to check'), [validators.DataRequired(), validators.URL(), validators.length(max=255)])
    http_method = SelectField(__('HTTP method to use'), choices=[(method.value, method.name) for method in MonitoringHttpMethod], default=MonitoringHttpMethod.GET.value)
    http_headers = TextAreaField(__('HTTP headers to send'))
    http_body_regex = StringField(__('HTTP response body Regex check'), [validators.length(max=255)])
    verify_https_cert = BooleanField(__('Verify HTTPS certificate?'), default=True)
    check_interval = IntegerField(__('Check interval (minutes)'), default=5)
    timeout = IntegerField(__('Connection timeout (seconds)'), default=10)
    email_recipients = TextAreaField(__('Recipients of the email alerts'))
    sms_recipients = TextAreaField(__('Recipients of the SMS alerts'))


# -----------------------------------------------------------
# CLI commands


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""
    db.drop_all()
    db.create_all()


@app.cli.command()
@click.option('--force', is_flag=True, default=False, help='Force checks whenever monitorings are due or not')
def check(force):
    """Perform all checks for the active monitorings."""
    lock_file = 'storage/.running'

    if os.path.isfile(lock_file):
        app.logger.warning('Checks already running, aborting')
        app.logger.warning('If Server Patrol crashed, please delete the storage/.running file before running this command again')
        app.logger.warning('If this happens too many times, please open an issue.')
        return

    open(lock_file, 'a').close() # Create the lock file

    app.logger.info('Getting all active monitorings')

    if force:
        app.logger.info('  Ignoring monitorings due')

    monitorings = Monitoring.query.get_for_checking()

    app.logger.info('{} monitorings to check'.format(len(monitorings)))

    for monitoring in monitorings:
        app.logger.info(monitoring.name)

        now = arrow.now().floor('minute')

        if not force and now < monitoring.next_check: # This monitoring isn't due
            app.logger.info('  Not due')
            continue

        status = MonitoringStatus.UP

        app.logger.info('  Checking: {} {}'.format(monitoring.http_method.value, monitoring.url))

        try:
            response = requests.request(monitoring.http_method.value, monitoring.url, timeout=monitoring.timeout, verify=monitoring.verify_https_cert, headers=monitoring.http_headers)
            response.raise_for_status()

            # Check for the response body if this monitoring is configured to do so
            if monitoring.http_body_regex and not re.match(monitoring.http_body_regex, response.text):
                raise InvalidResponseBody()
        except requests.exceptions.HTTPError:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('The server responded with an HTTP error: %(status_code)i %(reason)s.', status_code=response.status_code, reason=response.reason)
        except requests.exceptions.TooManyRedirects:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('There were too many HTTP redirects (3xx HTTP status code).')
        except requests.exceptions.ConnectTimeout:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('Connection to the server timed out.')
        except requests.exceptions.ReadTimeout:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('The server took too long to respond.')
        except requests.exceptions.SSLError as se:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('An SSL error occured: %(exception)s', exception=str(se))
        except requests.exceptions.ProxyError as pe:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('A proxy error occured: %(exception)s', exception=str(pe))
        except requests.exceptions.ConnectionError:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('Network error: unable to connect to the server.')
        except InvalidResponseBody:
            status = MonitoringStatus.DOWN
            monitoring.last_down_reason = _('Response body check failed: the Regex doesn\'t match anything.')

        app.logger.info('  ' + status.value + (' (' + monitoring.last_down_reason + ')' if status == MonitoringStatus.DOWN else ''))

        if monitoring.status != status: # The status is different from the one in DB: update it and send alerts if required
            app.logger.info('  Status is different')

            old_status_known = monitoring.status != MonitoringStatus.UNKNOWN

            monitoring.last_status_change_at = arrow.now()
            monitoring.status = status

            if old_status_known: # Only send alerts if the old status is known (i.e not a newly-created monitoring)
                if app.config['ENABLE_EMAIL_ALERTS'] and monitoring.email_recipients: # Email alerts enabled?
                    app.logger.info('  Sending emails to {}'.format(monitoring.email_recipients))

                    msg = Message()
                    msg.recipients = monitoring.email_recipients

                    if status == MonitoringStatus.DOWN: # The new status is down?
                        msg.subject = _('%(monitoring_name)s is gone', monitoring_name=monitoring.name)
                        msg.extra_headers = {
                            'X-Priority': '1',
                            'X-MSMail-Priority': 'High',
                            'Importance': 'High'
                        }
                    elif status == MonitoringStatus.UP: # The new status is up?
                        msg.subject = _('%(monitoring_name)s is back up', monitoring_name=monitoring.name)

                    msg.body = render_template('emails/status_changed.txt', monitoring=monitoring)
                    msg.html = render_template('emails/status_changed.html', monitoring=monitoring)

                    try:
                        mail.send(msg)
                    except Exception as e:
                        app.logger.error('  Error sending emails: {}'.format(e))

                if app.config['ENABLE_SMS_ALERTS'] and monitoring.sms_recipients: # SMS alerts enabled?
                    app.logger.info('  Sending SMS to {}'.format(monitoring.sms_recipients))

                    sms_body = render_template('sms/status_changed.txt', monitoring=monitoring)

                    twilio_client = twilio.rest.Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])

                    for sms_recipient in monitoring.sms_recipients:
                        try:
                            twilio_client.messages.create(
                                to=sms_recipient,
                                from_=app.config['TWILIO_SENDER_PHONE_NUMBER'],
                                body=sms_body
                            )

                            # Do not send more than one SMS per second
                            time.sleep(1)
                        except Exception as e:
                            app.logger.error('  Error sending SMS: {}'.format(e))

        monitoring.last_checked_at = now

        db.session.add(monitoring)
        db.session.commit()

    os.remove(lock_file)


# -----------------------------------------------------------
# Hooks


@app.before_request
def set_locale():
    if not hasattr(g, 'CURRENT_LOCALE'):
        if app.config['FORCE_LANGUAGE']:
            g.CURRENT_LOCALE = app.config['FORCE_LANGUAGE']
        else:
            g.CURRENT_LOCALE = request.accept_languages.best_match(app.config['LANGUAGES'].keys(), default=app.config['DEFAULT_LANGUAGE'])


@auth.get_password
def get_password(username):
    if username in app.config['USERS']:
        return app.config['USERS'].get(username)

    return None


@auth.error_handler
def auth_error():
    return http_error_handler(403, without_code=True)


@babel.localeselector
def get_app_locale():
    if not hasattr(g, 'CURRENT_LOCALE'):
        return app.config['DEFAULT_LANGUAGE']
    else:
        return g.CURRENT_LOCALE


# -----------------------------------------------------------
# HTTP errors handler


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(503)
def http_error_handler(error, without_code=False):
    if isinstance(error, HTTPException):
        error = error.code
    elif not isinstance(error, int):
        error = 500

    body = render_template('errors/{}.html'.format(error))

    if not without_code:
        return make_response(body, error)
    else:
        return make_response(body)


# -----------------------------------------------------------
# Exceptions


class InvalidResponseBody(Exception):
    pass
