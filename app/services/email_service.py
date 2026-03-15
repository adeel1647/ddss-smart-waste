from __future__ import annotations

import html
import logging
import resend

from app.core.config import settings

log = logging.getLogger(__name__)

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


def build_reset_code_email_html(code: str, app_name: str = "DDSS Smart Waste") -> str:
    import html

    safe_code = html.escape(code)

    logo_url = "https://v0-ddss-hull.vercel.app/logo.png"
    banner_url = "https://v0-ddss-hull.vercel.app/banner.webp"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{html.escape(app_name)} Password Reset</title>
    </head>
    <body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fb;padding:24px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                   style="max-width:600px;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">

              <!-- Top banner -->
              <tr>
                <td style="background:#0f172a;padding:20px 24px;text-align:center;">
                  <img src="{banner_url}"
                       alt="DDSS Smart Waste"
                       style="max-width:100%;height:auto;display:block;margin:0 auto 16px auto;border:0;" />
                  <img src="{logo_url}"
                       alt="DDSS Smart Waste Logo"
                       style="max-width:72px;height:auto;display:block;margin:0 auto 12px auto;border:0;" />
                  <h1 style="margin:0;font-size:24px;line-height:1.3;color:#ffffff;font-weight:700;">
                    DDSS Smart Waste
                  </h1>
                  <p style="margin:8px 0 0 0;font-size:14px;line-height:1.5;color:#cbd5e1;">
                    Decision Support System for IoT Waste Management
                  </p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:32px 28px;">
                  <h2 style="margin:0 0 16px 0;font-size:20px;line-height:1.4;color:#111827;">
                    Password Reset Verification
                  </h2>

                  <p style="margin:0 0 16px 0;font-size:15px;line-height:1.7;color:#374151;">
                    We received a request to reset your password for your DDSS Smart Waste account.
                  </p>

                  <p style="margin:0 0 20px 0;font-size:15px;line-height:1.7;color:#374151;">
                    Please use the 6-digit verification code below to continue:
                  </p>

                  <div style="text-align:center;margin:28px 0;">
                    <span style="
                      display:inline-block;
                      padding:16px 26px;
                      font-size:32px;
                      font-weight:700;
                      letter-spacing:8px;
                      color:#89c470;
                      background:#fffff;
                      border:1px solid #89c470;
                      border-radius:14px;
                    ">
                      {safe_code}
                    </span>
                  </div>

                  <p style="margin:0 0 10px 0;font-size:14px;line-height:1.6;color:#4b5563;">
                    This code will expire in <strong>10 minutes</strong>.
                  </p>

                  <p style="margin:0 0 10px 0;font-size:14px;line-height:1.6;color:#4b5563;">
                    If you did not request a password reset, you can safely ignore this email.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:20px 28px;background:#f9fafb;border-top:1px solid #e5e7eb;">
                  <p style="margin:0 0 6px 0;font-size:13px;line-height:1.5;color:#6b7280;">
                    DDSS Smart Waste Management
                  </p>
                  <p style="margin:0 0 6px 0;font-size:12px;line-height:1.5;color:#9ca3af;">
                    University of Hull
                  </p>
                  <p style="margin:0;font-size:12px;line-height:1.5;color:#9ca3af;">
                    This is an automated email. Please do not reply directly.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

def build_reset_code_email_text(code: str, app_name: str = "DDSS Smart Waste") -> str:
    return (
        "DDSS Smart Waste\n"
        "Decision Support System for IoT Waste Management\n"
        "University of Hull\n\n"
        "Password Reset Verification\n\n"
        f"Your 6-digit verification code is: {code}\n\n"
        "This code expires in 10 minutes.\n"
        "If you did not request this password reset, you can ignore this email.\n"
    )


def send_reset_code_email(email: str, code: str) -> dict:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    html_body = build_reset_code_email_html(code, settings.app_name)
    text_body = build_reset_code_email_text(code, settings.app_name)

    params: resend.Emails.SendParams = {
        "from": settings.mail_from,
        "to": [email],
        "subject": f"{settings.app_name} Password Reset Code",
        "html": html_body,
        "text": text_body,
    }

    try:
        response = resend.Emails.send(params)
        log.info("Password reset email sent to %s", email)
        return response
    except Exception:
        log.exception("Failed to send password reset email to %s", email)
        raise