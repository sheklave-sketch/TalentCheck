"""
Invitation service — sends email (SendGrid) and/or SMS (Africa's Talking).
"""
import httpx
from ..config import settings


async def send_email_invite(
    to_email: str,
    candidate_name: str,
    org_name: str,
    assessment_title: str,
    invite_url: str,
    expires_in_days: int = 7,
) -> bool:
    if not settings.SENDGRID_API_KEY:
        print(f"[DEV] Email invite would be sent to {to_email}: {invite_url}")
        return True

    payload = {
        "personalizations": [{"to": [{"email": to_email, "name": candidate_name}]}],
        "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": "TalentCheck"},
        "subject": f"You've been invited to complete an assessment for {org_name}",
        "content": [
            {
                "type": "text/html",
                "value": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #0A0E1A;">Hello {candidate_name},</h2>
                    <p>{org_name} has invited you to complete the <strong>{assessment_title}</strong> assessment.</p>
                    <p>This link is valid for <strong>{expires_in_days} days</strong> and is for your use only.</p>
                    <div style="margin: 32px 0;">
                        <a href="{invite_url}"
                           style="background: #F5A623; color: #0A0E1A; padding: 14px 28px;
                                  text-decoration: none; border-radius: 6px; font-weight: bold;">
                            Start Assessment
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        TalentCheck Ethiopia — Hire by Skill, Not CV
                    </p>
                </div>
                """,
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
            json=payload,
            timeout=10,
        )
    return resp.status_code == 202


async def send_sms_invite(
    phone: str,
    candidate_name: str,
    org_name: str,
    invite_url: str,
) -> bool:
    if not settings.AFRICAS_TALKING_API_KEY:
        print(f"[DEV] SMS invite would be sent to {phone}: {invite_url}")
        return True

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.africastalking.com/version1/messaging",
            headers={
                "ApiKey": settings.AFRICAS_TALKING_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "username": settings.AFRICAS_TALKING_USERNAME,
                "to": phone,
                "message": (
                    f"Hi {candidate_name}, {org_name} invites you to complete an assessment. "
                    f"Click: {invite_url} (expires in 7 days)"
                ),
            },
            timeout=10,
        )
    return resp.status_code == 201
