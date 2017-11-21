from sqlalchemy_utils import ArrowType
from serverpatrol import db, auth
from enum import Enum
import arrow
import json


__all__ = [
    'MonitoringHttpMethod',
    'MonitoringStatus',
    'Monitoring',
    'MonitoringCheck'
]


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
    _http_headers = db.Column('http_headers', db.Text, default={})
    http_body_regex = db.Column(db.String(255), default=None)
    verify_https_cert = db.Column(db.Boolean, default=True)
    check_interval = db.Column(db.Integer, default=5)
    timeout = db.Column(db.Integer, default=10)
    last_checked_at = db.Column(ArrowType, default=None)
    last_status_change_at = db.Column(ArrowType, default=None)
    status = db.Column(db.Enum(MonitoringStatus), default=MonitoringStatus.UNKNOWN)
    last_down_reason = db.Column(db.Text, default='')
    _email_recipients = db.Column('email_recipients', db.Text, default=[])
    _sms_recipients = db.Column('sms_recipients', db.Text, default=[])
    created_at = db.Column(ArrowType, default=arrow.now())
    ignore_http_errors = db.Column(db.Boolean, default=False)

    checks = db.relationship('MonitoringCheck', backref='monitoring', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return '<Monitoring> #{} : {}'.format(self.id, self.name)

    @property
    def next_check(self):
        if self.last_checked_at:
            attr = self.last_checked_at
        else:
            attr = self.created_at

        return attr.floor('minute').shift(minutes=self.check_interval)

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
        return json.loads(self._http_headers)

    @http_headers.setter
    def http_headers(self, value):
        if isinstance(value, str):
            self._http_headers = value
        else:
            self._http_headers = json.dumps(value)

    @property
    def email_recipients(self):
        return json.loads(self._email_recipients)

    @email_recipients.setter
    def email_recipients(self, value):
        if isinstance(value, str):
            self._email_recipients = value
        else:
            self._email_recipients = json.dumps(value)

    @property
    def sms_recipients(self):
        return json.loads(self._sms_recipients)

    @sms_recipients.setter
    def sms_recipients(self, value):
        if isinstance(value, str):
            self._sms_recipients = value
        else:
            self._sms_recipients = json.dumps(value)

    @property
    def request_duration_data(self):
        return [[check.date_time.timestamp * 1000, check.request_duration] for check in self.checks]


class MonitoringCheck(db.Model):
    class MonitoringCheckQuery(db.Query):
        pass

    __tablename__ = 'monitoring_checks'
    query_class = MonitoringCheckQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    date_time = db.Column(ArrowType, nullable=False)
    down_reason = db.Column(db.Text, default='')
    request_duration = db.Column(db.Integer, default=0)

    monitoring_id = db.Column(db.Integer, db.ForeignKey('monitorings.id'))

    def __repr__(self):
        return '<MonitoringCheck> #{} : {}'.format(self.id, self.monitoring)
