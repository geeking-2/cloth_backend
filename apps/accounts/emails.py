from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(user, token):
    link = f"{settings.FRONTEND_URL}/verify-email/{token.token}"
    subject = "Verify your CultureConnect account"
    html_message = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #7c3aed, #f97316); border-radius: 12px; line-height: 48px; color: white; font-weight: bold; font-size: 20px;">C</div>
            <h1 style="font-size: 24px; color: #111827; margin: 16px 0 0;">CultureConnect</h1>
        </div>
        <h2 style="font-size: 20px; color: #111827; text-align: center;">Verify your email address</h2>
        <p style="color: #6b7280; font-size: 15px; line-height: 1.6; text-align: center;">
            Hi {user.first_name or user.username},<br>
            Thanks for signing up! Please verify your email to activate your account.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 15px;">
                Verify Email Address
            </a>
        </div>
        <p style="color: #9ca3af; font-size: 13px; text-align: center;">
            This link expires in 24 hours. If you didn't create an account, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
        <p style="color: #9ca3af; font-size: 12px; text-align: center;">
            &copy; 2026 CultureConnect. Where Culture Meets XR Innovation.
        </p>
    </div>
    """
    plain_message = f"Hi {user.first_name or user.username}, verify your email: {link}"
    send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)


def send_password_reset_email(user, token):
    link = f"{settings.FRONTEND_URL}/reset-password/{token.token}"
    subject = "Reset your CultureConnect password"
    html_message = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #7c3aed, #f97316); border-radius: 12px; line-height: 48px; color: white; font-weight: bold; font-size: 20px;">C</div>
            <h1 style="font-size: 24px; color: #111827; margin: 16px 0 0;">CultureConnect</h1>
        </div>
        <h2 style="font-size: 20px; color: #111827; text-align: center;">Reset your password</h2>
        <p style="color: #6b7280; font-size: 15px; line-height: 1.6; text-align: center;">
            Hi {user.first_name or user.username},<br>
            We received a request to reset your password. Click the button below to create a new one.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 15px;">
                Reset Password
            </a>
        </div>
        <p style="color: #9ca3af; font-size: 13px; text-align: center;">
            This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
        <p style="color: #9ca3af; font-size: 12px; text-align: center;">
            &copy; 2026 CultureConnect. Where Culture Meets XR Innovation.
        </p>
    </div>
    """
    plain_message = f"Hi {user.first_name or user.username}, reset your password: {link}"
    send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)
