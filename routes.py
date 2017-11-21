from flask import render_template, abort, redirect, url_for, flash, g, Response
from serverpatrol import app, auth, db
from flask_babel import _, format_datetime
from models import *
from forms import *
import PyRSS2Gen


@app.route('/')
def home():
    return render_template('home.html', monitorings=Monitoring.query.get_for_home())


@app.route('/reports')
def reports():
    return render_template('reports.html', monitorings=Monitoring.query.get_for_home())


@app.route('/admin')
@auth.login_required
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

        date = monitoring.last_status_change_at if monitoring.last_status_change_at else monitoring.created_at

        rss_items.append(PyRSS2Gen.RSSItem(
            title=title,
            link=monitoring.url,
            description=description,
            guid=PyRSS2Gen.Guid(':'.join([str(monitoring.id), monitoring.status.value, date.format()]), isPermaLink=False),
            pubDate=date.datetime,
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
