from serverpatrol import app, db, mail
from flask import render_template
from flask_mail import Message
from flask_babel import _
from models import *
import twilio.rest
import requests
import click
import arrow
import math
import time
import os
import re


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""
    if not click.confirm('Are you sure?'):
        click.secho('Aborted', fg='red')

        return

    click.echo('Dropping everything')

    db.drop_all()

    click.echo('Creating tables')

    db.create_all()

    click.secho('Done', fg='green')


@app.cli.command()
@click.option('--force', is_flag=True, default=False, help='Force checks whenever monitorings are due or not')
def check(force):
    """Perform all checks for the active monitorings."""
    lock_file = 'storage/.running'

    if os.path.isfile(lock_file):
        click.echo('Checks already running, aborting', err=True)
        click.echo('Maybe Server Patrol crashed. Please delete the storage/.running file before running this command again.', err=True)
        click.echo('If this happens too many times, please open an issue.', err=True)

        return

    open(lock_file, 'a').close() # Create the lock file

    click.echo('Getting all active monitorings')

    if force:
        click.echo('  Ignoring monitorings due')

    monitorings = Monitoring.query.get_for_checking()

    click.echo('{} monitorings to check'.format(len(monitorings)))

    for monitoring in monitorings:
        click.echo(monitoring.name)

        now = arrow.now().floor('minute')

        if not force and now < monitoring.next_check: # This monitoring isn't due
            click.echo('  Not due')
            continue

        status = MonitoringStatus.UP

        click.echo('  Checking: {} {}'.format(monitoring.http_method.value, monitoring.url))

        try:
            response = requests.request(monitoring.http_method.value, monitoring.url, timeout=monitoring.timeout, verify=monitoring.verify_https_cert, headers=monitoring.http_headers)

            # Only raise an HTTPError exception if we don't allow error HTTP statuses
            if not monitoring.ignore_http_errors:
                response.raise_for_status()

            # Check the response body if this monitoring has a regex
            if monitoring.http_body_regex and not re.match(monitoring.http_body_regex, response.text):
                raise InvalidResponseBody()
        except requests.exceptions.HTTPError: # Should not be encountered if monitoring.ignore_http_errors == True
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

        click.echo('  ' + status.value + (' (' + monitoring.last_down_reason + ')' if status == MonitoringStatus.DOWN else ''))

        if monitoring.status != status: # The status is different from the one in DB: update it and send alerts if required
            click.echo('  Status is different')

            old_status_known = monitoring.status != MonitoringStatus.UNKNOWN

            monitoring.last_status_change_at = now
            monitoring.status = status

            if old_status_known: # Only send alerts if the old status is known (i.e not a newly-created monitoring)
                if app.config['ENABLE_EMAIL_ALERTS'] and monitoring.email_recipients: # Email alerts enabled?
                    click.echo('  Sending emails to {}'.format(monitoring.email_recipients))

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
                        click.echo('  Error sending emails: {}'.format(e))

                if app.config['ENABLE_SMS_ALERTS'] and monitoring.sms_recipients: # SMS alerts enabled?
                    click.echo('  Sending SMS to {}'.format(monitoring.sms_recipients))

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
                            click.echo('  Error sending SMS: {}'.format(e), err=True)

        monitoring.last_checked_at = now

        monitoring_check = MonitoringCheck()
        monitoring_check.monitoring = monitoring
        monitoring_check.date_time = now
        monitoring_check.down_reason = monitoring.last_down_reason if monitoring.status != MonitoringStatus.UP else ''
        monitoring_check.request_duration = math.floor(response.elapsed.total_seconds() * 1000) if monitoring.status == MonitoringStatus.UP else 0

        db.session.add(monitoring_check)

        db.session.add(monitoring)
        db.session.commit()

    os.remove(lock_file)

    click.secho('Done', fg='green')


class InvalidResponseBody(Exception):
    pass
