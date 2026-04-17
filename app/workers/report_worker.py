from __future__ import annotations

import asyncio

from app.db.session import AsyncSessionLocal
from app.services.reports_scheduler import run_due_reports


async def main():
    async with AsyncSessionLocal() as session:
        processed = await run_due_reports(session, limit=50)
        print(f"Processed {len(processed)} scheduled reports")


if __name__ == "__main__":
    asyncio.run(main())