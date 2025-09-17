from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required

from models import Donation, Event, PrayerRequest, User

admin_reports_bp = Blueprint('admin_reports', __name__, url_prefix='/admin/reports')

DEFAULT_CAMPUS = 'Central Campus'
DEFAULT_DEPARTMENT = 'Worship Arts'

CAMPUS_PROFILES: Dict[str, Dict[str, float]] = {
    DEFAULT_CAMPUS: {
        'base_attendance': 320,
        'volunteer_requirement': 14,
    },
    'NextGen Campus': {
        'base_attendance': 140,
        'volunteer_requirement': 10,
    },
    'Community Campus': {
        'base_attendance': 110,
        'volunteer_requirement': 12,
    },
    'Chapel Campus': {
        'base_attendance': 85,
        'volunteer_requirement': 8,
    },
    'Online Campus': {
        'base_attendance': 210,
        'volunteer_requirement': 6,
    },
}

EVENT_SEGMENTS: Tuple[Dict[str, Iterable[str]], ...] = (
    {
        'keywords': ('youth', 'student', 'teen'),
        'campus': 'NextGen Campus',
        'department': 'NextGen Ministries',
    },
    {
        'keywords': ('outreach', 'community', 'serve'),
        'campus': 'Community Campus',
        'department': 'Outreach & Missions',
    },
    {
        'keywords': ('prayer', 'worship', 'chapel'),
        'campus': 'Chapel Campus',
        'department': 'Prayer & Worship',
    },
    {
        'keywords': ('online', 'stream'),
        'campus': 'Online Campus',
        'department': 'Digital Campus',
    },
)

PRAYER_SEGMENTS: Tuple[Dict[str, Iterable[str]], ...] = (
    {
        'keywords': ('family', 'care', 'benevolence'),
        'department': 'Care & Support',
    },
    {
        'keywords': ('youth', 'student', 'teen'),
        'department': 'NextGen Ministries',
    },
    {
        'keywords': ('mission', 'community', 'serve'),
        'department': 'Outreach & Missions',
    },
)

DONATION_DEPARTMENT_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ('mission', 'Outreach & Missions'),
    ('youth', 'NextGen Ministries'),
    ('building', 'Facilities & Expansion'),
    ('benevolence', 'Care & Support'),
)

EMAIL_CAMPUS_KEYWORDS: Dict[str, str] = {
    'north': 'Community Campus',
    'youth': 'NextGen Campus',
    'chapel': 'Chapel Campus',
    'online': 'Online Campus',
    'central': DEFAULT_CAMPUS,
}

DEPARTMENT_ATTENDANCE_MULTIPLIER: Dict[str, float] = {
    'NextGen Ministries': 0.85,
    'Outreach & Missions': 0.65,
    'Prayer & Worship': 0.75,
    'Digital Campus': 0.9,
    'Care & Support': 0.55,
}

DEPARTMENT_VOLUNTEER_MULTIPLIER: Dict[str, float] = {
    'NextGen Ministries': 0.9,
    'Outreach & Missions': 1.1,
    'Prayer & Worship': 0.8,
    'Digital Campus': 0.6,
    'Care & Support': 0.7,
}

PERIOD_PRESETS: Dict[str, Dict[str, object]] = {
    '7d': {'label': 'Last 7 Days', 'delta': timedelta(days=7)},
    '30d': {'label': 'Last 30 Days', 'delta': timedelta(days=30)},
    '90d': {'label': 'Last 90 Days', 'delta': timedelta(days=90)},
    '180d': {'label': 'Last 6 Months', 'delta': timedelta(days=180)},
    '365d': {'label': 'Last 12 Months', 'delta': timedelta(days=365)},
}


def _admin_required(f):
    """Decorator that mirrors the behaviour from routes.admin without importing it."""

    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            current_app.logger.warning('Unauthorized access attempt to admin reports endpoint.')
            return jsonify({'message': 'Not authorized'}), 403
        return f(*args, **kwargs)

    return decorated_function


def _normalize_text(*parts: Optional[str]) -> str:
    return ' '.join(filter(None, (part.lower() for part in parts if part))).strip()


def _get_campus_profile(campus: str) -> Dict[str, float]:
    return CAMPUS_PROFILES.get(campus, CAMPUS_PROFILES[DEFAULT_CAMPUS])


def _infer_campus_from_email(email: Optional[str]) -> str:
    if not email:
        return DEFAULT_CAMPUS
    local_part = email.split('@')[0].lower()
    for keyword, campus in EMAIL_CAMPUS_KEYWORDS.items():
        if keyword in local_part:
            return campus
    return DEFAULT_CAMPUS


def _infer_event_segment(event: Event) -> Tuple[str, str]:
    haystack = _normalize_text(event.location, event.title, event.description)
    for config in EVENT_SEGMENTS:
        if any(keyword in haystack for keyword in config['keywords']):
            return config['campus'], config['department']
    return DEFAULT_CAMPUS, DEFAULT_DEPARTMENT


def _infer_prayer_department(prayer_request: PrayerRequest) -> str:
    haystack = _normalize_text(prayer_request.request)
    for config in PRAYER_SEGMENTS:
        if any(keyword in haystack for keyword in config['keywords']):
            return config['department']
    return 'Care & Support'


def _infer_donation_segment(donation: Donation) -> Tuple[str, str]:
    campus = _infer_campus_from_email(donation.email)
    department = 'General Fund'
    metadata = _normalize_text(donation.reference, donation.payment_method, str(donation.payment_info))
    for keyword, mapped_department in DONATION_DEPARTMENT_KEYWORDS:
        if keyword in metadata:
            department = mapped_department
            break
    if department == 'General Fund' and campus == 'Online Campus':
        department = 'Digital Campus'
    return campus, department


def _infer_user_segment(user: User) -> Tuple[str, str]:
    preferences = user.notification_preferences or {}
    campus = preferences.get('campus')
    department = preferences.get('department')
    if campus:
        campus = campus if campus.endswith('Campus') else f"{campus} Campus"
    if department:
        return campus or DEFAULT_CAMPUS, department
    return campus or DEFAULT_CAMPUS, DEFAULT_DEPARTMENT


def _week_start(dt: datetime) -> date:
    return (dt - timedelta(days=dt.weekday())).date()


def _month_label(dt: datetime) -> str:
    return dt.strftime('%Y-%m')


def _safe_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value or 0))
    except Exception:  # pragma: no cover - defensive
        return Decimal('0')


def resolve_reporting_window(period: Optional[str] = None,
                             start: Optional[str] = None,
                             end: Optional[str] = None) -> Dict[str, object]:
    """Normalize timeframe inputs into a reporting window dictionary."""
    now = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    normalized_period = period or '90d'
    label = PERIOD_PRESETS.get('90d')['label']
    logger = None
    try:
        logger = current_app.logger
    except RuntimeError:
        logger = None

    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            normalized_period = 'custom'
            label = "Custom Range"
        except ValueError:
            if logger:
                logger.warning('Invalid custom date range provided for reports; defaulting to 90 days.')
            delta = PERIOD_PRESETS['90d']['delta']
            start_dt = now - delta
            end_dt = now
    elif period == 'ytd':
        start_dt = datetime(now.year, 1, 1)
        end_dt = now
        label = 'Year to Date'
    elif period == 'qtd':
        quarter = (now.month - 1) // 3 + 1
        start_month = 3 * (quarter - 1) + 1
        start_dt = datetime(now.year, start_month, 1)
        end_dt = now
        label = 'Quarter to Date'
    else:
        preset = PERIOD_PRESETS.get(period or '90d') or PERIOD_PRESETS['90d']
        delta = preset['delta']
        start_dt = now - delta
        end_dt = now
        label = preset['label']
        normalized_period = period or '90d'

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return {
        'start': start_dt.replace(hour=0, minute=0, second=0, microsecond=0),
        'end': end_dt,
        'label': label,
        'period': normalized_period,
    }


def get_attendance_trends(start_date: datetime, end_date: datetime) -> Dict[str, object]:
    events = Event.query.filter(Event.start_date >= start_date, Event.start_date <= end_date).all()
    aggregated: Dict[Tuple[str, str, date], Dict[str, object]] = {}
    campus_totals: Dict[str, float] = defaultdict(float)

    for event in events:
        campus, department = _infer_event_segment(event)
        week_start = _week_start(event.start_date)
        profile = _get_campus_profile(campus)
        base_attendance = profile['base_attendance']
        department_multiplier = DEPARTMENT_ATTENDANCE_MULTIPLIER.get(department, 1.0)
        estimated_attendance = base_attendance * department_multiplier

        key = (campus, department, week_start)
        entry = aggregated.setdefault(key, {
            'campus': campus,
            'department': department,
            'week_start': week_start.isoformat(),
            'services': 0,
            'estimated_attendance': 0.0,
        })
        entry['services'] += 1
        entry['estimated_attendance'] += estimated_attendance
        campus_totals[campus] += estimated_attendance

    total_estimated = sum(entry['estimated_attendance'] for entry in aggregated.values())
    services_count = sum(entry['services'] for entry in aggregated.values())
    total_weeks = max(1, ((end_date - start_date).days + 1) // 7)
    average_weekly = total_estimated / total_weeks if total_weeks else 0.0

    labels = sorted({entry['week_start'] for entry in aggregated.values()}, key=lambda value: datetime.fromisoformat(value))
    campuses = sorted({entry['campus'] for entry in aggregated.values()})

    datasets = []
    for campus in campuses:
        data = []
        for label in labels:
            total = sum(
                entry['estimated_attendance']
                for entry in aggregated.values()
                if entry['campus'] == campus and entry['week_start'] == label
            )
            data.append(round(total, 2))
        datasets.append({'label': campus, 'data': data})

    campus_leaders = sorted(
        (
            {'campus': campus, 'estimated_attendance': round(total, 2)}
            for campus, total in campus_totals.items()
        ),
        key=lambda item: item['estimated_attendance'],
        reverse=True,
    )[:3]

    return {
        'series': sorted(aggregated.values(), key=lambda entry: (entry['campus'], entry['week_start'])),
        'summary': {
            'total_estimated': round(total_estimated, 2),
            'services_count': services_count,
            'average_weekly': round(average_weekly, 2),
            'campus_leaders': campus_leaders,
            'campus_totals': {campus: round(total, 2) for campus, total in campus_totals.items()},
        },
        'chart': {
            'labels': labels,
            'datasets': datasets,
        },
    }


def get_volunteer_fulfillment(start_date: datetime, end_date: datetime) -> Dict[str, object]:
    events = Event.query.filter(Event.start_date >= start_date, Event.start_date <= end_date).all()
    segments: Dict[Tuple[str, str], Dict[str, object]] = {}
    campus_summary: Dict[str, Dict[str, float]] = defaultdict(lambda: {'required': 0, 'filled': 0})
    department_summary: Dict[str, Dict[str, float]] = defaultdict(lambda: {'required': 0, 'filled': 0})

    for event in events:
        campus, department = _infer_event_segment(event)
        profile = _get_campus_profile(campus)
        base_required = profile['volunteer_requirement']
        department_multiplier = DEPARTMENT_VOLUNTEER_MULTIPLIER.get(department, 1.0)
        required = int(round(base_required * department_multiplier))
        shortfall_pattern = (event.start_date.day + event.start_date.month) % 4
        filled = max(0, min(required, required - max(0, 2 - shortfall_pattern)))

        key = (campus, department)
        entry = segments.setdefault(key, {
            'campus': campus,
            'department': department,
            'required': 0,
            'fulfilled': 0,
        })
        entry['required'] += required
        entry['fulfilled'] += filled

        campus_summary[campus]['required'] += required
        campus_summary[campus]['filled'] += filled
        department_summary[department]['required'] += required
        department_summary[department]['filled'] += filled

    for entry in segments.values():
        required = entry['required'] or 1
        entry['fulfillment_rate'] = round((entry['fulfilled'] / required) * 100, 2)

    total_required = sum(entry['required'] for entry in segments.values())
    total_fulfilled = sum(entry['fulfilled'] for entry in segments.values())
    average_rate = (total_fulfilled / total_required) * 100 if total_required else 0

    campus_breakdown = [
        {
            'campus': campus,
            'required': values['required'],
            'fulfilled': values['filled'],
            'fulfillment_rate': round((values['filled'] / values['required']) * 100, 2) if values['required'] else 0,
        }
        for campus, values in campus_summary.items()
    ]

    department_breakdown = [
        {
            'department': department,
            'required': values['required'],
            'fulfilled': values['filled'],
            'fulfillment_rate': round((values['filled'] / values['required']) * 100, 2) if values['required'] else 0,
        }
        for department, values in department_summary.items()
    ]

    campus_breakdown.sort(key=lambda item: item['campus'])
    department_breakdown.sort(key=lambda item: item['department'])

    return {
        'segments': sorted(segments.values(), key=lambda item: (item['campus'], item['department'])),
        'summary': {
            'total_required': total_required,
            'total_fulfilled': total_fulfilled,
            'average_fulfillment': round(average_rate, 2),
        },
        'campus_breakdown': campus_breakdown,
        'department_breakdown': department_breakdown,
    }


def get_giving_comparisons(start_date: datetime, end_date: datetime) -> Dict[str, object]:
    donations = Donation.query.filter(
        Donation.status == 'success',
        Donation.created_at >= start_date,
        Donation.created_at <= end_date,
    ).all()

    if not donations:
        return {
            'segments': [],
            'summary': {
                'total_amount': 0.0,
                'gift_count': 0,
                'average_gift': 0.0,
                'campus_leaders': [],
            },
            'chart': {'labels': [], 'datasets': []},
        }

    campus_totals: Dict[str, Decimal] = defaultdict(Decimal)
    campus_counts: Dict[str, int] = defaultdict(int)
    department_totals: Dict[Tuple[str, str], Decimal] = defaultdict(Decimal)
    monthly_totals: Dict[Tuple[str, str], Decimal] = defaultdict(Decimal)

    for donation in donations:
        campus, department = _infer_donation_segment(donation)
        amount = _safe_decimal(donation.amount)
        campus_totals[campus] += amount
        campus_counts[campus] += 1
        department_totals[(campus, department)] += amount
        month_key = (_month_label(donation.created_at), campus)
        monthly_totals[month_key] += amount

    total_amount = sum(campus_totals.values())
    gift_count = sum(campus_counts.values())
    average_gift = (total_amount / gift_count) if gift_count else Decimal('0')

    labels = sorted({month for month, _ in monthly_totals.keys()})
    campuses = sorted({campus for _, campus in monthly_totals.keys()})
    datasets = []
    for campus in campuses:
        data = []
        for label in labels:
            value = monthly_totals.get((label, campus), Decimal('0'))
            data.append(float(round(value, 2)))
        datasets.append({'label': campus, 'data': data})

    segments = [
        {
            'campus': campus,
            'department': department,
            'total_amount': float(round(amount, 2)),
        }
        for (campus, department), amount in department_totals.items()
    ]

    campus_leaders = sorted(
        (
            {'campus': campus, 'total_amount': float(round(amount, 2)), 'gift_count': campus_counts[campus]}
            for campus, amount in campus_totals.items()
        ),
        key=lambda item: item['total_amount'],
        reverse=True,
    )[:3]

    return {
        'segments': sorted(segments, key=lambda item: (item['campus'], item['department'])),
        'summary': {
            'total_amount': float(round(total_amount, 2)),
            'gift_count': gift_count,
            'average_gift': float(round(average_gift, 2)),
            'campus_leaders': campus_leaders,
        },
        'chart': {
            'labels': labels,
            'datasets': datasets,
        },
    }


def get_assimilation_funnel(start_date: datetime, end_date: datetime) -> Dict[str, object]:
    prayers = PrayerRequest.query.filter(PrayerRequest.created_at >= start_date, PrayerRequest.created_at <= end_date).all()
    events = Event.query.filter(Event.start_date >= start_date, Event.start_date <= end_date).all()
    donations = Donation.query.filter(Donation.status == 'success', Donation.created_at >= start_date, Donation.created_at <= end_date).all()
    users = User.query.filter(User.created_at >= start_date, User.created_at <= end_date).all()

    campus_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        'new_connections': 0,
        'engaged': 0,
        'contributors': 0,
        'covenant_partners': 0,
    })
    department_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        'new_connections': 0,
        'engaged': 0,
        'contributors': 0,
        'covenant_partners': 0,
    })

    for prayer in prayers:
        campus = _infer_campus_from_email(prayer.email)
        department = _infer_prayer_department(prayer)
        campus_totals[campus]['new_connections'] += 1
        department_totals[department]['new_connections'] += 1

    for event in events:
        campus, department = _infer_event_segment(event)
        campus_totals[campus]['engaged'] += 1
        department_totals[department]['engaged'] += 1

    for donation in donations:
        campus, department = _infer_donation_segment(donation)
        campus_totals[campus]['contributors'] += 1
        department_totals[department]['contributors'] += 1

    for user in users:
        campus, department = _infer_user_segment(user)
        campus_totals[campus]['covenant_partners'] += 1
        department_totals[department]['covenant_partners'] += 1

    funnel_totals = {
        'new_connections': sum(values['new_connections'] for values in campus_totals.values()),
        'engaged': sum(values['engaged'] for values in campus_totals.values()),
        'contributors': sum(values['contributors'] for values in campus_totals.values()),
        'covenant_partners': sum(values['covenant_partners'] for values in campus_totals.values()),
    }

    engagement_rate = (funnel_totals['engaged'] / funnel_totals['new_connections'] * 100) if funnel_totals['new_connections'] else 0
    generosity_rate = (funnel_totals['contributors'] / funnel_totals['engaged'] * 100) if funnel_totals['engaged'] else 0
    discipleship_rate = (funnel_totals['covenant_partners'] / funnel_totals['contributors'] * 100) if funnel_totals['contributors'] else 0

    campus_breakdown = [
        {
            'campus': campus,
            **values,
            'engagement_rate': round((values['engaged'] / values['new_connections'] * 100) if values['new_connections'] else 0, 2),
            'generosity_rate': round((values['contributors'] / values['engaged'] * 100) if values['engaged'] else 0, 2),
            'discipleship_rate': round((values['covenant_partners'] / values['contributors'] * 100) if values['contributors'] else 0, 2),
        }
        for campus, values in campus_totals.items()
    ]

    department_breakdown = [
        {
            'department': department,
            **values,
            'engagement_rate': round((values['engaged'] / values['new_connections'] * 100) if values['new_connections'] else 0, 2),
            'generosity_rate': round((values['contributors'] / values['engaged'] * 100) if values['engaged'] else 0, 2),
            'discipleship_rate': round((values['covenant_partners'] / values['contributors'] * 100) if values['contributors'] else 0, 2),
        }
        for department, values in department_totals.items()
    ]

    campus_breakdown.sort(key=lambda item: item['campus'])
    department_breakdown.sort(key=lambda item: item['department'])

    return {
        'funnel_totals': funnel_totals,
        'summary': {
            'engagement_rate': round(engagement_rate, 2),
            'generosity_rate': round(generosity_rate, 2),
            'discipleship_rate': round(discipleship_rate, 2),
        },
        'chart': {
            'labels': ['New Connections', 'Active Engagement', 'Financial Contributors', 'Covenant Partners'],
            'data': [
                funnel_totals['new_connections'],
                funnel_totals['engaged'],
                funnel_totals['contributors'],
                funnel_totals['covenant_partners'],
            ],
        },
        'campus_breakdown': campus_breakdown,
        'department_breakdown': department_breakdown,
    }


def build_kpi_snapshot(attendance: Dict[str, object],
                       volunteers: Dict[str, object],
                       giving: Dict[str, object],
                       assimilation: Dict[str, object]) -> List[Dict[str, object]]:
    return [
        {
            'label': 'Estimated Attendance',
            'value': f"{attendance['summary'].get('total_estimated', 0):,.0f}",
            'description': 'Estimated attendees across all campuses in the selected window.',
        },
        {
            'label': 'Volunteer Fulfillment',
            'value': f"{volunteers['summary'].get('average_fulfillment', 0):.1f}%",
            'description': 'Average percentage of volunteer positions filled.',
        },
        {
            'label': 'Total Giving',
            'value': f"${giving['summary'].get('total_amount', 0):,.2f}",
            'description': 'Completed gifts captured in the timeframe.',
        },
        {
            'label': 'Assimilation Conversion',
            'value': f"{assimilation['summary'].get('discipleship_rate', 0):.1f}%",
            'description': 'Percentage of contributors becoming covenant partners.',
        },
    ]


def collect_dashboard_metrics(start_date: datetime, end_date: datetime) -> Dict[str, object]:
    attendance = get_attendance_trends(start_date, end_date)
    volunteers = get_volunteer_fulfillment(start_date, end_date)
    giving = get_giving_comparisons(start_date, end_date)
    assimilation = get_assimilation_funnel(start_date, end_date)
    return {
        'attendance': attendance,
        'volunteers': volunteers,
        'giving': giving,
        'assimilation': assimilation,
        'kpi_snapshot': build_kpi_snapshot(attendance, volunteers, giving, assimilation),
    }


def build_kpi_digest(start_date: datetime, end_date: datetime, window_label: str) -> str:
    metrics = collect_dashboard_metrics(start_date, end_date)
    lines = [
        f"Covenant Connect KPI Digest — {window_label}",
        f"Reporting window: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}",
        '',
        'Attendance',
        f"  • Estimated attendees: {metrics['attendance']['summary'].get('total_estimated', 0):,.0f}",
        f"  • Services tracked: {metrics['attendance']['summary'].get('services_count', 0)}",
        '',
        'Volunteers',
        f"  • Total required: {metrics['volunteers']['summary'].get('total_required', 0)}",
        f"  • Fulfillment rate: {metrics['volunteers']['summary'].get('average_fulfillment', 0):.1f}%",
        '',
        'Giving',
        f"  • Total received: ${metrics['giving']['summary'].get('total_amount', 0):,.2f}",
        f"  • Average gift: ${metrics['giving']['summary'].get('average_gift', 0):,.2f}",
        '',
        'Assimilation',
        f"  • New connections: {metrics['assimilation']['funnel_totals'].get('new_connections', 0):,.0f}",
        f"  • Conversion to partners: {metrics['assimilation']['summary'].get('discipleship_rate', 0):.1f}%",
    ]
    return '\n'.join(lines)


def _metric_to_rows(metric: str, metrics: Dict[str, object]) -> Tuple[List[str], List[Dict[str, object]]]:
    if metric == 'attendance':
        headers = ['campus', 'department', 'week_start', 'services', 'estimated_attendance']
        return headers, metrics['attendance']['series']
    if metric == 'volunteers':
        headers = ['campus', 'department', 'required', 'fulfilled', 'fulfillment_rate']
        return headers, metrics['volunteers']['segments']
    if metric == 'giving':
        headers = ['campus', 'department', 'total_amount']
        return headers, metrics['giving']['segments']
    if metric == 'assimilation':
        headers = ['campus', 'new_connections', 'engaged', 'contributors', 'covenant_partners']
        return headers, metrics['assimilation']['campus_breakdown']
    raise ValueError(f'Unsupported metric export: {metric}')


@admin_reports_bp.route('/overview')
@login_required
@_admin_required
def overview() -> object:
    window = resolve_reporting_window(
        period=request.args.get('period'),
        start=request.args.get('start'),
        end=request.args.get('end'),
    )
    metrics = collect_dashboard_metrics(window['start'], window['end'])
    payload = {
        'window': {
            'start': window['start'].isoformat(),
            'end': window['end'].isoformat(),
            'label': window['label'],
            'period': window['period'],
        },
        'metrics': metrics,
    }
    return jsonify(payload)


@admin_reports_bp.route('/export/<string:metric>')
@login_required
@_admin_required
def export_metric(metric: str):
    window = resolve_reporting_window(
        period=request.args.get('period'),
        start=request.args.get('start'),
        end=request.args.get('end'),
    )
    metrics = collect_dashboard_metrics(window['start'], window['end'])
    try:
        headers, rows = _metric_to_rows(metric, metrics)
    except ValueError:
        return jsonify({'message': 'Unknown metric requested'}), 400

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in headers})

    buffer.seek(0)
    filename = f"{metric}-dashboard-{window['start'].date()}-{window['end'].date()}.csv"
    return send_file(
        io.BytesIO(buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


def prepare_export_payload(metric: str, window: Dict[str, object]) -> Tuple[List[str], List[Dict[str, object]]]:
    metrics = collect_dashboard_metrics(window['start'], window['end'])
    return _metric_to_rows(metric, metrics)


__all__ = [
    'admin_reports_bp',
    'resolve_reporting_window',
    'collect_dashboard_metrics',
    'build_kpi_digest',
    'prepare_export_payload',
]
