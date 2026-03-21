import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert import AlertRule
from app.models.machine import Machine
from app.models.company import Company

logger = logging.getLogger("pcmonitor.notifier")


async def send_alert_notification(db: AsyncSession, rule: AlertRule, machine: Machine, value: float):
    company = None
    if machine.company_id:
        result = await db.execute(select(Company).where(Company.id == machine.company_id))
        company = result.scalar_one_or_none()

    if rule.notify_email:
        await send_email_alert(rule, machine, value, company)
    if rule.notify_telegram:
        await send_telegram_alert(rule, machine, value, company)


async def send_email_alert(
    rule: AlertRule, machine: Machine, value: float, company: Optional[Company] = None
):
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured, skipping email alert")
        return

    to_email = None
    if company and company.alert_email:
        to_email = company.alert_email
    elif settings.ALERT_EMAIL:
        to_email = settings.ALERT_EMAIL

    if not to_email:
        logger.warning("No recipient email configured (set ALERT_EMAIL in .env), skipping email alert")
        return

    subject = f"[{rule.severity.upper()}] {rule.name} — {machine.hostname}"
    dashboard_link = f"{settings.DASHBOARD_URL}/machines/{machine.id}"
    company_name = company.name if company else "Unknown"

    html_body = f"""
    <html>
    <body style="background:#000;color:#94a3b8;font-family:Inter,sans-serif;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:rgba(10,18,32,0.9);
                    border:1px solid rgba(45,212,191,0.3);border-radius:12px;padding:24px;">
            <img src="{settings.DASHBOARD_URL}/logo.png" width="160" alt="Numbers10" style="margin-bottom:16px;" />
            <h2 style="color:#e0f7fa;font-family:'Space Grotesk',sans-serif;margin:0 0 8px;">
                Alert: {rule.name}
            </h2>
            <p style="color:#2dd4bf;margin:0 0 16px;">Severity: {rule.severity.upper()}</p>
            <table style="width:100%;color:#94a3b8;font-size:14px;">
                <tr><td style="padding:4px 8px;">Company:</td><td style="color:#e0f7fa;">{company_name}</td></tr>
                <tr><td style="padding:4px 8px;">Machine:</td><td style="color:#e0f7fa;">{machine.hostname}</td></tr>
                <tr><td style="padding:4px 8px;">Metric:</td><td style="color:#e0f7fa;">{rule.metric_field}</td></tr>
                <tr><td style="padding:4px 8px;">Current Value:</td>
                    <td style="color:#ef4444;font-family:'JetBrains Mono',monospace;font-weight:bold;">{value}</td></tr>
                <tr><td style="padding:4px 8px;">Threshold:</td>
                    <td style="color:#e0f7fa;">{rule.operator} {rule.threshold}</td></tr>
            </table>
            <a href="{dashboard_link}"
               style="display:inline-block;margin-top:16px;padding:10px 24px;
                      background:#2dd4bf;color:#000;text-decoration:none;
                      border-radius:8px;font-weight:bold;">
                View in Dashboard →
            </a>
        </div>
    </body>
    </html>
    """

    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_PORT == 465,
            start_tls=settings.SMTP_PORT == 587,
        )
        logger.info(f"Email alert sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")


async def send_telegram_alert(
    rule: AlertRule, machine: Machine, value: float, company: Optional[Company] = None
):
    token = settings.TELEGRAM_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if company and company.telegram_chat_id:
        chat_id = company.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured, skipping alert")
        return

    company_name = company.name if company else "Unknown"
    severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(rule.severity, "⚪")

    message = (
        f"{severity_emoji} <b>Alert: {rule.name}</b>\n\n"
        f"<b>Company:</b> {company_name}\n"
        f"<b>Machine:</b> {machine.hostname}\n"
        f"<b>Metric:</b> {rule.metric_field}\n"
        f"<b>Value:</b> <code>{value}</code> ({rule.operator} {rule.threshold})\n"
        f"<b>Severity:</b> {rule.severity.upper()}\n\n"
        f'<a href="{settings.DASHBOARD_URL}/machines/{machine.id}">View Dashboard →</a>'
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"Telegram alert sent: {rule.name}")
            else:
                logger.error(f"Telegram API error: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
