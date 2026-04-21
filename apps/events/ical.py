"""
Hand-rolled iCalendar (RFC 5545) generator. No external deps.

Produces VCALENDAR payloads for single events, tickets, bookings, and
per-user aggregated feeds.
"""
from datetime import datetime, timezone as _tz
from django.conf import settings


def _fmt_dt(dt):
    """Format a datetime as iCal UTC (yyyymmddThhmmssZ)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return dt.astimezone(_tz.utc).strftime('%Y%m%dT%H%M%SZ')


def _fmt_date(d):
    return d.strftime('%Y%m%d')


def _escape(text):
    if text is None:
        return ''
    # RFC 5545: escape backslash, semicolon, comma, newline
    return (str(text)
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\r\n', '\\n')
            .replace('\n', '\\n'))


def _fold(line):
    """iCal lines should be folded at 75 octets. Most readers are forgiving,
    but let's be correct for long descriptions."""
    if len(line) <= 75:
        return line
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(' ' + rest[:74])
        rest = rest[74:]
    return '\r\n'.join(parts)


def _vevent(uid, summary, dtstart, dtend, description='', location='', url='', all_day=False):
    """Return list of lines for a single VEVENT block."""
    dt_func = _fmt_date if all_day else _fmt_dt
    dt_prop = 'DTSTART;VALUE=DATE' if all_day else 'DTSTART'
    dte_prop = 'DTEND;VALUE=DATE' if all_day else 'DTEND'
    lines = [
        'BEGIN:VEVENT',
        _fold(f'UID:{uid}'),
        _fold(f'DTSTAMP:{_fmt_dt(datetime.now(_tz.utc))}'),
        _fold(f'{dt_prop}:{dt_func(dtstart)}'),
        _fold(f'{dte_prop}:{dt_func(dtend)}'),
        _fold(f'SUMMARY:{_escape(summary)}'),
    ]
    if description:
        lines.append(_fold(f'DESCRIPTION:{_escape(description)}'))
    if location:
        lines.append(_fold(f'LOCATION:{_escape(location)}'))
    if url:
        lines.append(_fold(f'URL:{url}'))
    lines.append('END:VEVENT')
    return lines


def build_ical(vevent_lists, cal_name='CultureConnect'):
    """Given a list of VEVENT line lists, wrap in a VCALENDAR."""
    header = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//CultureConnect//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_escape(cal_name)}',
    ]
    footer = ['END:VCALENDAR']
    body = []
    for vevent in vevent_lists:
        body.extend(vevent)
    return '\r\n'.join(header + body + footer) + '\r\n'


def event_vevent(event):
    """VEVENT for a CultureConnect Event."""
    site = getattr(settings, 'SITE_URL', 'https://cultureconnect-e4d4e201dfdb.herokuapp.com').rstrip('/')
    return _vevent(
        uid=f'event-{event.id}@cultureconnect',
        summary=event.title,
        dtstart=event.starts_at,
        dtend=event.ends_at or event.starts_at,
        description=(event.description or '')[:1000],
        location=event.location_text or (event.space.title if getattr(event, 'space', None) else ''),
        url=f'{site}/events/{event.slug}',
    )


def ticket_vevent(ticket):
    return _vevent(
        uid=f'ticket-{ticket.id}@cultureconnect',
        summary=f'🎟 {ticket.event.title}',
        dtstart=ticket.event.starts_at,
        dtend=ticket.event.ends_at or ticket.event.starts_at,
        description=f'Your ticket — show the QR code at the door. Tier: {ticket.tier.name}.',
        location=ticket.event.location_text or '',
    )


def booking_vevent(booking):
    return _vevent(
        uid=f'booking-{booking.id}@cultureconnect',
        summary=f'📅 {booking.space.title} (booked)',
        dtstart=booking.start_date,
        dtend=booking.end_date,
        description=f'Confirmed booking at {booking.space.title}.',
        location=getattr(booking.space.venue, 'address', '') or getattr(booking.space.venue, 'city', '') or '',
        all_day=True,
    )
