"""Weekly 'what's happening this week' digest email.

Gathers upcoming public events in the next 7 days, filters by the recipient's
city where possible, and sends a lightweight HTML summary. Designed to be fired
from a management command by Heroku Scheduler.

Idempotency: we don't persist a 'sent' flag per user because the scheduler runs
at a fixed weekly cadence; running twice in the same week just re-sends. Good
enough for now — switch to a DigestSend model if we need stricter guarantees.
"""
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def _collect_events():
    """Public events starting in the next 7 days, soonest first."""
    from .models import Event
    now = timezone.now()
    horizon = now + timedelta(days=7)
    return (Event.objects
            .filter(is_public=True, starts_at__gte=now, starts_at__lte=horizon)
            .select_related('space__venue', 'host')
            .order_by('starts_at'))


def _event_location(ev):
    if ev.space_id and ev.space:
        venue = getattr(ev.space, 'venue', None)
        city = getattr(venue, 'city', '') if venue else ''
        return f'{ev.space.title}{" · " + city if city else ""}'
    return ev.location_text or ''


def _event_city(ev):
    if ev.space_id and ev.space and getattr(ev.space, 'venue', None):
        return (ev.space.venue.city or '').strip().lower()
    return ''


def _recipient_city(user):
    for attr in ('city',):
        v = getattr(user, attr, '')
        if v:
            return v.strip().lower()
    # Creator + audience + venue profiles all use a `city` field.
    for prof_attr in ('creator_profile', 'audience_profile', 'venue_profile'):
        prof = getattr(user, prof_attr, None)
        if prof is None:
            continue
        v = getattr(prof, 'city', '') or ''
        if v:
            return v.strip().lower()
    return ''


def _html_for(user, events, site_url):
    name = user.first_name or user.username
    blocks = []
    for ev in events[:8]:
        when = timezone.localtime(ev.starts_at).strftime('%a %b %-d · %-I:%M %p') if hasattr(ev.starts_at, 'strftime') else str(ev.starts_at)
        where = _event_location(ev)
        blocks.append(f"""
        <tr><td style="padding:12px 0;border-bottom:1px solid #f3f4f6;">
          <a href="{site_url}/events/{ev.slug}" style="color:#111827;text-decoration:none;font-weight:600;font-size:16px;">{ev.title}</a>
          <div style="color:#6b7280;font-size:13px;margin-top:4px;">{when}{'  ·  ' + where if where else ''}</div>
        </td></tr>
        """)
    list_html = ''.join(blocks) or '<tr><td style="color:#9ca3af;">Nothing on the calendar this week — check back next Monday.</td></tr>'

    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:560px;margin:0 auto;padding:40px 20px;">
      <div style="text-align:center;margin-bottom:28px;">
        <div style="display:inline-block;width:44px;height:44px;background:linear-gradient(135deg,#7c3aed,#f97316);border-radius:10px;line-height:44px;color:white;font-weight:bold;font-size:18px;">C</div>
        <h1 style="font-size:22px;color:#111827;margin:14px 0 0;">This week on CultureConnect</h1>
      </div>
      <p style="color:#6b7280;font-size:15px;line-height:1.6;">
        Hi {name} — here's what's happening in the next 7 days.
      </p>
      <table style="width:100%;border-collapse:collapse;margin-top:18px;">
        {list_html}
      </table>
      <div style="text-align:center;margin:32px 0 0;">
        <a href="{site_url}/feed" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:white;text-decoration:none;border-radius:10px;font-weight:600;font-size:14px;">
          See everything
        </a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:32px 0;">
      <p style="color:#9ca3af;font-size:12px;text-align:center;">
        You're receiving this because your CultureConnect digest is on.
        <br>
        <a href="{site_url}/settings" style="color:#9ca3af;">Update preferences</a>
      </p>
    </div>
    """


def send_weekly_digest(dry_run=False, limit=None):
    """Returns (sent_count, skipped_count)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    events = list(_collect_events())
    if not events:
        return (0, 0)

    site_url = getattr(settings, 'FRONTEND_URL', 'https://cultureconnect-e4d4e201dfdb.herokuapp.com').rstrip('/')
    recipients = User.objects.filter(is_active=True).exclude(email='')
    if limit:
        recipients = recipients[:limit]

    sent, skipped = 0, 0
    for user in recipients:
        # Opt-out flag — respect a `digest_opt_in` boolean if the model has one.
        if hasattr(user, 'digest_opt_in') and user.digest_opt_in is False:
            skipped += 1
            continue

        city = _recipient_city(user)
        if city:
            local = [e for e in events if _event_city(e) == city]
            picks = local if local else events  # Fall back to global list
        else:
            picks = events

        html = _html_for(user, picks, site_url)
        plain = f"This week on CultureConnect — visit {site_url}/feed"
        if dry_run:
            sent += 1
            continue
        try:
            send_mail(
                subject='This week on CultureConnect',
                message=plain,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html,
                fail_silently=True,
            )
            sent += 1
        except Exception:
            skipped += 1
    return (sent, skipped)
