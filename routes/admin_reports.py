"""Aggregated reporting queries for administrative dashboards."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Iterable, List

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required

from app import db
from models import AttendanceRecord, Donation, Event, Member, VolunteerAssignment, VolunteerRole


admin_reports_bp = Blueprint('admin_reports', __name__, url_prefix='/admin/reports')


def admin_required(func):  # pragma: no cover - simple decorator
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return Response(status=403)
        return func(*args, **kwargs)

    return wrapper


class ReportingService:
    """Provide segmentation utilities for leadership dashboards and digests."""

    def __init__(self, session):
        self.session = session

    def attendance_trends(self, start: datetime, end: datetime) -> dict:
        query = (
            self.session.query(AttendanceRecord, Event)
            .join(Event, AttendanceRecord.event_id == Event.id)
            .filter(AttendanceRecord.check_in_time >= start)
            .filter(AttendanceRecord.check_in_time <= end)
        )

        campuses: dict[str, dict] = {}
        total_expected = 0
        total_checked = 0

        for record, event in query:
            campus = (event.campus or event.location or 'Main Campus').strip() or 'Main Campus'
            department_name = event.department.name if event.department else 'General'
            date_key = record.check_in_time.date().isoformat()

            campus_bucket = campuses.setdefault(
                campus,
                {'timeline': {}, 'departments': {}, 'expected': 0, 'checked': 0},
            )

            timeline_bucket = campus_bucket['timeline'].setdefault(
                date_key, {'expected': 0, 'checked': 0}
            )
            timeline_bucket['expected'] += record.expected_attendees or 0
            timeline_bucket['checked'] += record.checked_in_count or 0

            dept_bucket = campus_bucket['departments'].setdefault(
                department_name, {'expected': 0, 'checked': 0}
            )
            dept_bucket['expected'] += record.expected_attendees or 0
            dept_bucket['checked'] += record.checked_in_count or 0

            campus_bucket['expected'] += record.expected_attendees or 0
            campus_bucket['checked'] += record.checked_in_count or 0
            total_expected += record.expected_attendees or 0
            total_checked += record.checked_in_count or 0

        campuses_payload = []
        for campus, data in campuses.items():
            timeline = [
                {'date': date_key, 'expected': values['expected'], 'checked': values['checked']}
                for date_key, values in sorted(data['timeline'].items())
            ]
            departments = [
                {'name': name, 'expected': values['expected'], 'checked': values['checked']}
                for name, values in sorted(data['departments'].items())
            ]
            campuses_payload.append(
                {
                    'campus': campus,
                    'expected': data['expected'],
                    'checked': data['checked'],
                    'timeline': timeline,
                    'departments': departments,
                    'attendance_rate': self._rate(data['checked'], data['expected']),
                }
            )

        return {
            'total_expected': total_expected,
            'total_checked': total_checked,
            'attendance_rate': self._rate(total_checked, total_expected),
            'campuses': campuses_payload,
        }

    def volunteer_fulfilment(self, start: datetime, end: datetime) -> dict:
        roles = (
            self.session.query(VolunteerRole)
            .outerjoin(VolunteerRole.assignments)
            .outerjoin(VolunteerRole.department)
            .all()
        )

        department_totals: dict[str, dict[str, float]] = {}
        role_rows: List[dict] = []

        for role in roles:
            active_assignments = [
                assignment
                for assignment in role.assignments
                if self._assignment_active(assignment, start, end)
            ]
            assigned = len(active_assignments)
            needed = role.needed_volunteers or 1
            department_name = role.department.name if role.department else 'General'

            department_bucket = department_totals.setdefault(
                department_name,
                {'assigned': 0, 'needed': 0},
            )
            department_bucket['assigned'] += assigned
            department_bucket['needed'] += needed

            role_rows.append(
                {
                    'department': department_name,
                    'role': role.name,
                    'needed': needed,
                    'assigned': assigned,
                    'rate': self._rate(assigned, needed),
                }
            )

        departments = [
            {
                'department': name,
                'assigned': values['assigned'],
                'needed': values['needed'],
                'rate': self._rate(values['assigned'], values['needed']),
            }
            for name, values in sorted(department_totals.items())
        ]

        overall_needed = sum(values['needed'] for values in department_totals.values()) or 0
        overall_assigned = sum(values['assigned'] for values in department_totals.values()) or 0

        return {
            'roles': role_rows,
            'departments': departments,
            'overall_rate': self._rate(overall_assigned, overall_needed),
        }

    def giving_summary(self, start: datetime, end: datetime) -> dict:
        donations = (
            self.session.query(Donation)
            .filter(Donation.created_at >= start)
            .filter(Donation.created_at <= end)
            .all()
        )

        by_currency: dict[str, float] = {}
        by_method: dict[str, float] = {}
        monthly: dict[str, float] = {}
        total = 0.0

        for donation in donations:
            amount = float(donation.amount or 0)
            total += amount
            by_currency.setdefault(donation.currency or 'USD', 0.0)
            by_currency[donation.currency or 'USD'] += amount
            by_method.setdefault(donation.payment_method or 'unknown', 0.0)
            by_method[donation.payment_method or 'unknown'] += amount
            key = (donation.created_at or start).strftime('%Y-%m')
            monthly.setdefault(key, 0.0)
            monthly[key] += amount

        return {
            'total': total,
            'by_currency': by_currency,
            'by_method': by_method,
            'monthly': [
                {'month': month, 'amount': amount}
                for month, amount in sorted(monthly.items())
            ],
        }

    def assimilation_funnel(self, start: datetime, end: datetime) -> dict:
        members = (
            self.session.query(Member)
            .filter(Member.created_at >= start)
            .filter(Member.created_at <= end)
            .all()
        )

        funnel_order = [
            ('guest', 'Guests'),
            ('regular', 'Regular Attenders'),
            ('member', 'Members'),
            ('serve_team', 'Serving'),
        ]
        stage_totals = {label: 0 for _, label in funnel_order}
        campus_totals: dict[str, dict[str, int]] = {}

        for member in members:
            stage_key = (member.assimilation_stage or member.membership_status or 'guest').lower()
            label = None
            for key, friendly in funnel_order:
                if key in stage_key:
                    label = friendly
                    break
            if not label:
                label = 'Guests'

            stage_totals[label] += 1
            campus = (member.campus or 'Main Campus').strip() or 'Main Campus'
            campus_bucket = campus_totals.setdefault(campus, {stage: 0 for stage in stage_totals})
            campus_bucket[label] += 1

        stages = [{'label': label, 'count': stage_totals[label]} for _, label in funnel_order]

        campuses = [
            {
                'campus': campus,
                'stages': [{'label': label, 'count': values[label]} for _, label in funnel_order],
            }
            for campus, values in sorted(campus_totals.items())
        ]

        return {
            'total_members': len(members),
            'stages': stages,
            'campuses': campuses,
        }

    @staticmethod
    def _rate(numerator: float, denominator: float) -> float:
        if not denominator:
            return 0.0
        return round((numerator / denominator) * 100, 2)

    @staticmethod
    def _assignment_active(assignment: VolunteerAssignment, start: datetime, end: datetime) -> bool:
        start_date = assignment.start_date or start.date()
        end_date = assignment.end_date or end.date()
        return start_date <= end.date() and end_date >= start.date()


def _parse_window() -> tuple[datetime, datetime]:
    from routes.admin import _parse_timeframe  # lazy import to avoid cycle

    return _parse_timeframe(request.args.get('range'))


@admin_reports_bp.route('/metrics')
@login_required
@admin_required
def metrics():
    start, end = _parse_window()
    service = ReportingService(db.session)
    payload = {
        'attendance': service.attendance_trends(start, end),
        'volunteers': service.volunteer_fulfilment(start, end),
        'giving': service.giving_summary(start, end),
        'assimilation': service.assimilation_funnel(start, end),
    }
    return jsonify(payload)


def _csv_response(filename: str, rows: Iterable[List[str]]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    response = Response(buffer.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@admin_reports_bp.route('/attendance.csv')
@login_required
@admin_required
def export_attendance() -> Response:
    start, end = _parse_window()
    service = ReportingService(db.session)
    report = service.attendance_trends(start, end)

    rows = [['Campus', 'Date', 'Checked In', 'Expected']]
    for campus in report['campuses']:
        for entry in campus['timeline']:
            rows.append([campus['campus'], entry['date'], entry['checked'], entry['expected']])
    return _csv_response('attendance.csv', rows)


@admin_reports_bp.route('/volunteers.csv')
@login_required
@admin_required
def export_volunteers() -> Response:
    start, end = _parse_window()
    service = ReportingService(db.session)
    report = service.volunteer_fulfilment(start, end)

    rows = [['Department', 'Role', 'Needed', 'Assigned', 'Fill Rate %']]
    for role in report['roles']:
        rows.append(
            [
                role['department'],
                role['role'],
                role['needed'],
                role['assigned'],
                role['rate'],
            ]
        )
    return _csv_response('volunteers.csv', rows)


@admin_reports_bp.route('/giving.csv')
@login_required
@admin_required
def export_giving() -> Response:
    start, end = _parse_window()
    service = ReportingService(db.session)
    report = service.giving_summary(start, end)

    rows = [['Currency', 'Amount']]
    for currency, amount in report['by_currency'].items():
        rows.append([currency, f'{amount:.2f}'])
    rows.append([])
    rows.append(['Method', 'Amount'])
    for method, amount in report['by_method'].items():
        rows.append([method, f'{amount:.2f}'])
    return _csv_response('giving.csv', rows)


@admin_reports_bp.route('/assimilation.csv')
@login_required
@admin_required
def export_assimilation() -> Response:
    start, end = _parse_window()
    service = ReportingService(db.session)
    report = service.assimilation_funnel(start, end)

    header = ['Campus'] + [stage['label'] for stage in report['stages']]
    rows = [header]
    for campus in report['campuses']:
        row = [campus['campus']]
        for stage in campus['stages']:
            row.append(stage['count'])
        rows.append(row)
    return _csv_response('assimilation.csv', rows)


__all__ = ['ReportingService', 'admin_reports_bp']
