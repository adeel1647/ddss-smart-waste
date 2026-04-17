from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.enterprise import NotificationChannel, NotificationEvent
from app.services.notifiers import (
    send_email_notification,
    send_sms_notification,
    send_webhook_notification,
    send_in_app_notification,
)


async def dispatch_notification_event(
    session: AsyncSession,
    event: NotificationEvent,
) -> NotificationEvent:
    try:
        channel = None
        if event.channel_id is not None:
            channel = await session.get(NotificationChannel, event.channel_id)

        if channel is None:
            event.status = "failed"
            event.error_message = "No channel associated with event"
            await session.commit()
            await session.refresh(event)
            return event

        if not channel.enabled:
            event.status = "failed"
            event.error_message = "Channel is disabled"
            await session.commit()
            await session.refresh(event)
            return event

        payload = event.payload or {}
        subject = payload.get("title", event.event_type)
        message = payload.get("message", str(payload))

        if channel.channel_type == "email":
            result = await send_email_notification(channel.target, subject, message)
        elif channel.channel_type == "sms":
            result = await send_sms_notification(channel.target, message)
        elif channel.channel_type == "webhook":
            result = await send_webhook_notification(channel.target, payload)
        elif channel.channel_type == "in_app":
            result = await send_in_app_notification(channel.target, payload)
        else:
            event.status = "failed"
            event.error_message = f"Unsupported channel type: {channel.channel_type}"
            await session.commit()
            await session.refresh(event)
            return event

        if result.get("ok"):
            event.status = "sent"
            event.sent_at = datetime.now(timezone.utc)
            event.error_message = None
        else:
            event.status = "failed"
            event.error_message = result.get("provider_message", "Unknown dispatch failure")

        await session.commit()
        await session.refresh(event)
        return event

    except Exception as exc:
        event.status = "failed"
        event.error_message = str(exc)
        await session.commit()
        await session.refresh(event)
        return event


async def dispatch_queued_events(session: AsyncSession, limit: int = 25) -> list[NotificationEvent]:
    rows = await session.scalars(
        select(NotificationEvent)
        .where(NotificationEvent.status.in_(["queued", "pending"]))
        .order_by(NotificationEvent.created_at.asc())
        .limit(limit)
    )
    events = list(rows)

    processed: list[NotificationEvent] = []
    for event in events:
        processed.append(await dispatch_notification_event(session, event))
    return processed