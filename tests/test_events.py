import re
from datetime import datetime, timedelta

from werkzeug.datastructures import MultiDict

from app import db
from models import Event


def _get_csrf_token(client, path):
    response = client.get(path)
    match = re.search(r"name='csrf_token' value='([^']+)'", response.data.decode())
    assert match, 'CSRF token not found in planning form.'
    return match.group(1)


def _create_event(app):
    with app.app_context():
        start = datetime.utcnow().replace(microsecond=0)
        event = Event(
            title='Sunday Gathering',
            description='Weekly worship service.',
            start_date=start,
            end_date=start + timedelta(hours=2),
            location='Main Auditorium',
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def test_plan_event_updates_segments_and_tags(client, app):
    event_id = _create_event(app)
    token = _get_csrf_token(client, f'/events/plan/{event_id}')

    form_data = MultiDict(
        [
            ('csrf_token', token),
            ('recurrence_rule', 'FREQ=WEEKLY;BYDAY=SU'),
            ('recurrence_end', '2030-12-31'),
            ('ministry_tags', 'Worship, Production'),
            ('segment_title', 'Pre-service Prayer'),
            ('segment_leader', 'Prayer Lead'),
            ('segment_duration', '15 min'),
            ('segment_notes', 'Volunteers and staff'),
            ('segment_title', 'Worship Set'),
            ('segment_leader', 'Worship Pastor'),
            ('segment_duration', '25 min'),
            ('segment_notes', 'Songs TBD'),
        ]
    )

    response = client.post(
        f'/events/plan/{event_id}',
        data=form_data,
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.recurrence_rule == 'FREQ=WEEKLY;BYDAY=SU'
        assert event.recurrence_end_date is not None
        assert 'Worship' in (event.ministry_tags or [])
        assert len(event.service_segments or []) == 2


def test_events_json_feed_filters_by_tag(client, app):
    first_event_id = _create_event(app)
    with app.app_context():
        first_event = db.session.get(Event, first_event_id)
        first_event.ministry_tags = ['Worship']
        db.session.commit()

        start = datetime.utcnow().replace(microsecond=0)
        second_event = Event(
            title='Youth Night',
            description='Youth gathering and activities.',
            start_date=start + timedelta(days=1),
            end_date=start + timedelta(days=1, hours=2),
            location='Youth Center',
            ministry_tags=['Youth'],
        )
        db.session.add(second_event)
        db.session.commit()

    response = client.get('/api/events.json?tag=Youth')
    data = response.get_json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]['title'] == 'Youth Night'
    assert data[0]['ministry_tags'] == ['Youth']


def test_events_ical_feed_contains_rrule_and_categories(client, app):
    event_id = _create_event(app)
    with app.app_context():
        event = db.session.get(Event, event_id)
        event.recurrence_rule = 'FREQ=MONTHLY;BYDAY=SU'
        event.ministry_tags = ['Outreach', 'Community']
        db.session.commit()

    response = client.get('/api/events.ics')
    body = response.data.decode()

    assert 'BEGIN:VCALENDAR' in body
    assert 'RRULE:FREQ=MONTHLY;BYDAY=SU' in body
    assert 'CATEGORIES:Outreach,Community' in body
