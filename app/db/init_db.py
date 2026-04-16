from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine
from app.db.models import Base


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS address_line_1 VARCHAR(160);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS address_line_2 VARCHAR(160);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS city VARCHAR(80);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS county VARCHAR(80);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS country VARCHAR(80) DEFAULT 'United Kingdom';
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS formatted_address VARCHAR(255);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS geocode_place_id VARCHAR(120);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS geocode_source VARCHAR(32);
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS geocode_confidence DOUBLE PRECISION;
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS collection_interval_days INTEGER NOT NULL DEFAULT 7;
        """))
        await conn.execute(text("""
            ALTER TABLE bins ADD COLUMN IF NOT EXISTS collection_weekday INTEGER;
        """))