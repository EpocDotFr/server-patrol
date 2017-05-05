# Server Patrol

Simple HTTP-based server status check tool with email/SMS alerts.

<p align="center">
  <img src="https://github.com/EpocDotFr/server-patrol/raw/master/screenshot.png">
</p>

## Features

  - Manage multiple monitorings (URLs to check)
  - Check the network connection as well as 4XX and 5XX HTTP errors
  - Simple visualization of each monitorings status (down, up, unknown) with their respective down reason
  - RSS feed of the monitorings status (public monitorings only)
  - Responsive (can be used on mobile devices)
  - Ability to configure, for each monitorings:
    - HTTP method to use, connection timeout and if the HTTPS certificate have to be verified
    - Availability (enabled or disabled)
    - Public visibility
    - Check interval
    - (Optional) Email recipients and/or mobile phone numbers who will receive the status alerts
    - (Optional) A [Regex](https://en.wikipedia.org/wiki/Regular_expression) to perform a HTTP response body check
  - Internationalized & localized in 2 languages:
    - English (`en`)
    - French (`fr`)

## Prerequisites

  - Should work on any Python 3.x version. Feel free to test with another Python version and give me feedback
  - A [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)-capable web server (optional, but recommended)
  - (Optional) A [SMTP](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol) server to send email alerts
  - (Optional) A [Twilio](https://www.twilio.com/) account to send SMS alerts

## Installation

  1. Clone this repo somewhere
  2. `pip install -r requirements.txt`
  3. `pybabel compile -d translations`
  4. `export FLASK_APP=serverpatrol.py` (Windows users: `set FLASK_APP=serverpatrol.py`)
  5. `flask create_database` (WARNING: don't re-run this command unless you want to start from scratch, it will wipe out all the Server Patrol's data)
  6. Create the scheduled task that will run the script who will perform the checks every minutes (only for active monitorings that are due):

On a **Linux-based OS**, create this [Cron](https://en.wikipedia.org/wiki/Cron) entry:

```
* * * * * cd /path/to/server-patrol && sh bin/check.sh 2>&1
```

On **Windows**, create this scheduled task using the command line:

```
schtasks /create /tn "Server Patrol" /tr "cd C:\path\to\server-patrol && bin\check" /sc MINUTE
```

## Configuration

Copy the `config.example.py` file to `config.py` and fill in the configuration parameters.

Available configuration parameters are:

  - `SECRET_KEY` Set this to a complex random value
  - `DEBUG` Enable/disable debug mode
  - `LOGGER_HANDLER_POLICY` Policy of the default logging handler

More informations on the three above can be found [here](http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values).

  - `USERS` The credentials required to access the app. You can specify multiple ones. **It is highly recommended to serve Server Patrol through HTTPS** because it uses [HTTP basic auth](https://en.wikipedia.org/wiki/Basic_access_authentication)
  - `SERVER_NAME` The IP or hostname where Server Patrol will be available
  - `FORCE_LANGUAGE` Force the lang to be one of the supported ones (defaults to `None`: auto-detection from the `Accept-Language` HTTP header). See in the features section above for a list of available lang keys
  - `DEFAULT_LANGUAGE` Default language if it cannot be determined automatically. Not taken into account if `FORCE_LANGUAGE` is defined. See in the features section above for a list of available lang keys

SMTP-related parameters to send email alerts:

  - `ENABLE_EMAIL_ALERTS` Wheter to enable the email feature or not. If `True`, fill in the configuration parameters below
  - `MAIL_SERVER` The SMTP server name / IP to use to send email alerts
  - `MAIL_PORT` The SMTP server port
  - `MAIL_USE_TLS` Use TLS when connecting to the SMTP server?
  - `MAIL_USE_SSL` Use SSL when connecting to the SMTP server?
  - `MAIL_USERNAME` Username to use to connect to the SMTP server
  - `MAIL_PASSWORD` Password to use to connect to the SMTP server
  - `MAIL_DEFAULT_SENDER` A Python tuple to define the identity of the Server Patrol's mail sender

More configuration parameters can be added about SMTP configuration, see [here](https://pythonhosted.org/Flask-Mail/#configuring-flask-mail).

Twilio-related parameters to send SMS alerts:

  - `ENABLE_SMS_ALERTS` Wheter to enable the SMS feature or not. If `True`, fill in the configuration parameters below
  - `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are your Twilio credentials
  - `TWILIO_SENDER_PHONE_NUMBER` The Twilio phone number that will send the SMS

I'll let you search yourself about how to configure a web server along uWSGI.

## Usage

As you can see, Server Patrol is split in two pieces:

  - A Flask command (`flask check`) to run the checks (run `flask check --help` for the full list of arguments)
  - A Flask web app (the Server Patrol GUI) itself

You can run the web app:

  - Standalone

Run the internal web server, which will be accessible at `http://localhost:8080`:

```
python local.py
```

Edit this file and change the interface/port as needed.

  - uWSGI

The uWSGI file you'll have to set in your uWSGI configuration is `uwsgi.py`. The callable is `app`.

  - Others

You'll probably have to hack with this application to make it work with one of the solutions described [here](http://flask.pocoo.org/docs/0.12/deploying/). Send me a pull request if you make it work.

## How it works

This project is built on [Flask](http://flask.pocoo.org/) (Python) for the backend which is using a small [SQLite](https://en.wikipedia.org/wiki/SQLite)
database to persist data. [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol) requests are used to check the configured monitorings via
the `flask check` command.

## End words

If you have questions or problems, you can [submit an issue](https://github.com/EpocDotFr/server-patrol/issues).

You can also submit pull requests. It's open-source man!