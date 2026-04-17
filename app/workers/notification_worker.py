from __future__ import annotations

import asyncio

from app.db.session import AsyncSessionLocal
from app.services.notifications_dispatcher import dispatch_queued_events


async def main():
    async with AsyncSessionLocal() as session:
        processed = await dispatch_queued_events(session, limit=50)
        print(f"Processed {len(processed)} notification events")


if __name__ == "__main__":
    asyncio.run(main())