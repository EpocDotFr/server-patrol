# Server Patrol

Simple HTTP-based server status check tool with email alerts.

<p align="center">
  <img src="https://github.com/EpocDotFr/server-patrol/raw/master/screenshot.png">
</p>

## Features

  - Manage multiple monitorings (URLs to check)
  - Each monitorings status (down, up, unknow) are visible on a web page
  - RSS feed available for all monitorings
  - (Optional) Mails can be sent via SMTP when something happen
  - Ability to configure, for each monitorings:
    - HTTP method to use, as well as the connection timeout and if the HTTPS certificate have to be verified
    - Enable / disable the monitoring
    - Make the monitoring publicly visible or not
    - Check interval
    - List of email recipients who will receive alerts

## Prerequisites

  - Should work on any Python 3.x version. Feel free to test with another Python version and give me feedback
  - A [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)-capable web server (optional, but recommended)

## Installation

  1. Clone this repo somewhere
  2. `pip install -r requirements.txt`
  3. Create this [Cron](https://en.wikipedia.org/wiki/Cron) entry:

```
* * * * * cd /path/to/server-patrol && export FLASK_APP=serverpatrol.py && flask check 2>&1
```

This will run the checks every minutes for every active monitorings that are due.

## Configuration

Copy the `config.example.py` file to `config.py` and fill in the configuration parameters.

Available configuration parameters are:

  - `SECRET_KEY` Set this to a complex random value
  - `DEBUG` Enable/disable debug mode
  - `LOGGER_HANDLER_POLICY` Policy of the default logging handler

More informations on the three above can be found [here](http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values).

  - `USERS` The credentials required to access the app. You can specify multiple ones. **It is highly recommended to serve Server Patrol through HTTPS** because it uses [HTTP basic auth](https://en.wikipedia.org/wiki/Basic_access_authentication)
  - `SERVER_NAME` The IP or hostname where Server Patrol will be available

SMTP related parameters:

  - `MAIL_SERVER` The SMTP server
  - `MAIL_PORT` The SMTP port
  - `MAIL_USE_TLS` Use TLS when connecting to the SMTP server?
  - `MAIL_USE_SSL` Use SSL when connecting to the SMTP server?
  - `MAIL_USERNAME` Username to use to connect to the SMTP server
  - `MAIL_PASSWORD` Password to use to connect to the SMTP server
  - `MAIL_DEFAULT_SENDER` A Python tuple to define the identity of the Server Patrol's mail sender

More configuration parameters can be added about SMTP configuration, see [here](https://pythonhosted.org/Flask-Mail/#configuring-flask-mail).

I'll let you search yourself about how to configure a web server along uWSGI.

## Usage

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
database to persist data. [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol) requests are used to check the configured monitorings.

## End words

If you have questions or problems, you can [submit an issue](https://github.com/EpocDotFr/server-patrol/issues).

You can also submit pull requests. It's open-source man!