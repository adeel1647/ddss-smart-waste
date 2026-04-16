from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Site
from app.utils.polygon import point_in_polygon_geojson


async def find_site_for_point(
    session: AsyncSession,
    *,
    organisation_id: int | None,
    lat: float,
    lon: float,
) -> Site | None:
    stmt = select(Site).where(Site.is_active.is_(True))

    if organisation_id is not None:
        stmt = stmt.where(Site.organisation_id == organisation_id)

    result = await session.execute(stmt.order_by(Site.id.asc()))
    sites = list(result.scalars().all())

    for site in sites:
        if point_in_polygon_geojson(lat, lon, site.boundary_geojson):
            return site

    return None