from django.core.mail import send_mail
from django.conf import settings


def _email_layout(title, body_html):
    return f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #7c3aed, #f97316); border-radius: 12px; line-height: 48px; color: white; font-weight: bold; font-size: 20px;">C</div>
            <h1 style="font-size: 24px; color: #111827; margin: 16px 0 0;">CultureConnect</h1>
        </div>
        <h2 style="font-size: 20px; color: #111827; text-align: center;">{title}</h2>
        {body_html}
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
        <p style="color: #9ca3af; font-size: 12px; text-align: center;">&copy; 2026 CultureConnect</p>
    </div>
    """


def send_booking_request_email(booking):
    venue_user = booking.space.venue.user
    frontend = settings.FRONTEND_URL
    body = f"""
    <p style="color: #6b7280; font-size: 15px; line-height: 1.6;">
        Hi {venue_user.first_name or venue_user.username},<br><br>
        <strong>{booking.creator.display_name}</strong> has booked
        <strong>{booking.space.title}</strong> from <strong>{booking.start_date}</strong> to <strong>{booking.end_date}</strong>.
        <br><br>Total: <strong>${booking.total_amount}</strong>. Payment is authorized but not yet captured - review and accept to charge the card.
    </p>
    <div style="text-align: center; margin: 32px 0;">
        <a href="{frontend}/venue/bookings" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; text-decoration: none; border-radius: 12px; font-weight: 600;">Review Booking</a>
    </div>
    """
    try:
        send_mail(
            f'New booking request for {booking.space.title}',
            f'New booking: {frontend}/venue/bookings',
            settings.DEFAULT_FROM_EMAIL,
            [venue_user.email],
            html_message=_email_layout('New booking request', body),
        )
    except Exception:
        pass


def send_booking_accepted_email(booking):
    creator_user = booking.creator.user
    frontend = settings.FRONTEND_URL
    body = f"""
    <p style="color: #6b7280; font-size: 15px; line-height: 1.6;">
        Your booking at <strong>{booking.space.title}</strong> has been accepted! Payment of <strong>${booking.total_amount}</strong> has been charged.
        <br><br>Dates: <strong>{booking.start_date}</strong> to <strong>{booking.end_date}</strong>.
    </p>
    <div style="text-align: center; margin: 32px 0;">
        <a href="{frontend}/creator/bookings" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #10b981, #059669); color: white; text-decoration: none; border-radius: 12px; font-weight: 600;">View Booking</a>
    </div>
    """
    try:
        send_mail(
            f'Booking confirmed at {booking.space.title}!',
            f'Confirmed: {frontend}/creator/bookings',
            settings.DEFAULT_FROM_EMAIL,
            [creator_user.email],
            html_message=_email_layout('Booking confirmed! 🎉', body),
        )
    except Exception:
        pass


def send_booking_cancelled_email(booking):
    venue_user = booking.space.venue.user
    frontend = settings.FRONTEND_URL
    body = f"""
    <p style="color: #6b7280; font-size: 15px; line-height: 1.6;">
        Hi {venue_user.first_name or venue_user.username},<br><br>
        <strong>{booking.creator.display_name}</strong> has cancelled their booking at
        <strong>{booking.space.title}</strong> for <strong>{booking.start_date}</strong> to <strong>{booking.end_date}</strong>.
        <br><br>The payment authorization has been released and no charge was made.
        Those dates are now free on your calendar again.
    </p>
    <div style="text-align: center; margin: 32px 0;">
        <a href="{frontend}/venue/bookings" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; text-decoration: none; border-radius: 12px; font-weight: 600;">View bookings</a>
    </div>
    """
    try:
        send_mail(
            f'Booking cancelled - {booking.space.title}',
            f'Cancelled: {frontend}/venue/bookings',
            settings.DEFAULT_FROM_EMAIL,
            [venue_user.email],
            html_message=_email_layout('Booking cancelled', body),
        )
    except Exception:
        pass


def send_booking_rejected_email(booking):
    creator_user = booking.creator.user
    frontend = settings.FRONTEND_URL
    reason = booking.rejection_reason or 'No reason provided.'
    body = f"""
    <p style="color: #6b7280; font-size: 15px; line-height: 1.6;">
        Your booking at <strong>{booking.space.title}</strong> was declined. <strong>Your card was not charged</strong> - the authorization has been released.
        <br><br><strong>Reason:</strong> {reason}
    </p>
    <div style="text-align: center; margin: 32px 0;">
        <a href="{frontend}/search" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; text-decoration: none; border-radius: 12px; font-weight: 600;">Find another space</a>
    </div>
    """
    try:
        send_mail(
            f'Booking declined - {booking.space.title}',
            f'Declined: {reason}',
            settings.DEFAULT_FROM_EMAIL,
            [creator_user.email],
            html_message=_email_layout('Booking not accepted', body),
        )
    except Exception:
        pass
