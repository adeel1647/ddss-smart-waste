from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def next_bin_id(session: AsyncSession) -> str:
    r = await session.execute(text("SELECT nextval('public.bin_seq')"))
    n = r.scalar_one()
    return f"BN-{n:06d}"