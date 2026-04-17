from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import ScheduledReport, NotificationChannel, NotificationEvent


def report_is_due(report: ScheduledReport) -> bool:
    # simple placeholder logic
    # later you can use croniter for real cron support
    if not report.enabled:
        return False
    if report.last_run_at is None:
        return True
    return False


async def run_due_reports(session: AsyncSession, limit: int = 20) -> list[ScheduledReport]:
    rows = await session.scalars(
        select(ScheduledReport)
        .where(ScheduledReport.enabled == True)  # noqa: E712
        .order_by(ScheduledReport.created_at.asc())
        .limit(limit)
    )
    reports = list(rows)

    processed: list[ScheduledReport] = []

    for report in reports:
        if not report_is_due(report):
            continue

        first_email_channel = await session.scalar(
            select(NotificationChannel)
            .where(
                NotificationChannel.organisation_id == report.organisation_id,
                NotificationChannel.channel_type == "email",
                NotificationChannel.enabled == True,  # noqa: E712
            )
            .order_by(NotificationChannel.created_at.asc())
            .limit(1)
        )

        event = NotificationEvent(
            organisation_id=report.organisation_id,
            channel_id=first_email_channel.id if first_email_channel else None,
            event_type="report.ready",
            payload={
                "title": f"Scheduled report ready: {report.name}",
                "message": f"Report {report.name} has been generated in {report.format.upper()} format.",
                "report_type": report.report_type,
                "format": report.format,
                "recipients": report.recipients,
            },
            status="queued",
        )
        session.add(event)

        report.last_run_at = datetime.now(timezone.utc)
        processed.append(report)

    await session.commit()
    return processed