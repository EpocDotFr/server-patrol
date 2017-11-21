from wtforms import StringField, BooleanField, SelectField, IntegerField, TextAreaField
from flask_babel import lazy_gettext as __
from flask_wtf import FlaskForm
from models import *
import wtforms.validators as validators


__all__ = [
    'MonitoringForm'
]


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
    ignore_http_errors = BooleanField(__('Ignore HTTP errors?'), default=False)
