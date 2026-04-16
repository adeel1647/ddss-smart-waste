from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


class GeocodingError(Exception):
    pass


@dataclass
class ResolvedAddress:
    place_id: str | None
    display_name: str
    formatted_address: str
    lat: float
    lon: float
    postcode: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    county: str | None
    country: str | None
    source: str = "postcoder"
    confidence: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "display_name": self.display_name,
            "formatted_address": self.formatted_address,
            "lat": self.lat,
            "lon": self.lon,
            "postcode": self.postcode,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "city": self.city,
            "county": self.county,
            "country": self.country,
            "source": self.source,
            "confidence": self.confidence,
        }


def normalize_postcode(value: str | None) -> str | None:
    if not value:
        return None
    compact = " ".join(value.upper().strip().split())
    return compact or None


def postcode_sector_from_postcode(postcode: str | None) -> str | None:
    postcode = normalize_postcode(postcode)
    if not postcode:
        return None
    parts = postcode.split()
    if not parts:
        return None
    outward = parts[0]
    inward = parts[1] if len(parts) > 1 else ""
    if not inward:
        return outward
    return f"{outward} {inward[0]}"


def compose_free_text_query(
    *,
    postcode: str | None = None,
    address_line_1: str | None = None,
    address_line_2: str | None = None,
    city: str | None = None,
    county: str | None = None,
    country: str | None = None,
    formatted_address: str | None = None,
    query: str | None = None,
) -> str:
    if query:
        return query.strip()
    if formatted_address:
        return formatted_address.strip()

    parts = [
        address_line_1,
        address_line_2,
        city,
        county,
        postcode,
        country or settings.geocode_default_country,
    ]
    return ", ".join([p.strip() for p in parts if p and p.strip()])


class GeocodingService:
    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "User-Agent": settings.geocode_user_agent,
            "Accept-Language": settings.geocode_accept_language,
            "Accept": "application/json",
        }

    @staticmethod
    def _looks_like_postcode(value: str) -> bool:
        value = normalize_postcode(value) or ""
        return len(value.replace(" ", "")) >= 5

    @classmethod
    async def _request(cls, path: str, *, params: dict[str, Any] | None = None) -> Any:
        if not settings.geocode_api_key:
            raise GeocodingError("GEOCODE_API_KEY is not configured")

        base = settings.geocode_base_url.rstrip("/")
        url = f"{base}{path}"

        async with httpx.AsyncClient(
            timeout=settings.geocode_timeout_seconds,
            headers=cls._headers(),
        ) as client:
            res = await client.get(url, params=params or {})
            if res.status_code >= 400:
                detail = res.text.strip()[:300]
                raise GeocodingError(f"Geocoding request failed: {res.status_code} {detail}")
            return res.json()

    @staticmethod
    def _to_resolved(item: dict[str, Any]) -> ResolvedAddress:
        summary = str(
            item.get("summaryline")
            or item.get("addressline1")
            or item.get("postcode")
            or ""
        ).strip()

        address_line_1 = item.get("addressline1")
        address_line_2 = item.get("addressline2")
        address_line_3 = item.get("addressline3")

        formatted_parts = [address_line_1, address_line_2, address_line_3]
        formatted_address = ", ".join([str(x).strip() for x in formatted_parts if x and str(x).strip()])
        if not formatted_address:
            formatted_address = summary

        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            raise GeocodingError("Selected address does not include coordinates")

        postcode = normalize_postcode(item.get("postcode"))
        country = item.get("country") or settings.geocode_default_country
        place_id = (
            str(item.get("udprn"))
            if item.get("udprn") is not None
            else summary
        )

        return ResolvedAddress(
            place_id=place_id,
            display_name=summary or formatted_address,
            formatted_address=formatted_address,
            lat=float(lat),
            lon=float(lon),
            postcode=postcode,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=item.get("posttown"),
            county=item.get("county"),
            country=country,
            source="postcoder",
            confidence=1.0,
        )

    @classmethod
    async def _postcoder_address_search(
        cls,
        search_term: str,
        *,
        limit: int,
        postcode_only: bool,
    ) -> list[ResolvedAddress]:
        search_term = (search_term or "").strip()
        if not search_term:
            return []

        path = f"/pcw/{settings.geocode_api_key}/address/uk/{quote(search_term)}"

        params: dict[str, Any] = {
            "format": "json",
            "lines": 3,
            "include": "county,posttown,postcode",
            "addtags": "latitude,longitude,udprn",
            "postcodeonly": "true" if postcode_only else "false",
            "page": 0,
            # residential only; remove this if you want businesses too
            # "usercategory": "R",
        }

        results: list[ResolvedAddress] = []
        next_page: int | None = 0

        while next_page is not None and len(results) < limit:
            params["page"] = next_page
            payload = await cls._request(path, params=params)

            if not isinstance(payload, list):
                raise GeocodingError("Unexpected response from Postcoder")

            if not payload:
                break

            for item in payload:
                try:
                    results.append(cls._to_resolved(item))
                except Exception:
                    continue
                if len(results) >= limit:
                    break

            next_page = None
            last = payload[-1] if payload else None
            if isinstance(last, dict) and str(last.get("morevalues")).lower() == "true":
                raw_next = last.get("nextpage")
                try:
                    next_page = int(raw_next)
                except Exception:
                    next_page = None

        return results[:limit]

    @classmethod
    async def search(cls, q: str, *, limit: int | None = None) -> list[ResolvedAddress]:
        query = (q or "").strip()
        if not query:
            return []

        limit = max(1, min(limit or settings.geocode_limit, 25))
        is_postcode = cls._looks_like_postcode(query)

        return await cls._postcoder_address_search(
            query,
            limit=limit,
            postcode_only=is_postcode,
        )

    @classmethod
    async def lookup_place(
        cls,
        place_id: str,
        *,
        display_name: str | None = None,
        postcode: str | None = None,
    ) -> ResolvedAddress:
        # In this implementation, place_id is usually UDPRN or summaryline.
        # We fall back to a direct search using postcode/display text because
        # the frontend already sends lat/lon for selected results.
        search_text = postcode or display_name or place_id
        results = await cls.search(search_text, limit=1)
        if not results:
            raise GeocodingError("No address match found")
        return results[0]

    @classmethod
    async def resolve(
        cls,
        *,
        place_id: str | None = None,
        query: str | None = None,
        postcode: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        city: str | None = None,
        county: str | None = None,
        country: str | None = None,
        formatted_address: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        allow_manual_override: bool = False,
    ) -> ResolvedAddress:
        if lat is not None and lon is not None and (place_id or allow_manual_override):
            display_name = formatted_address or compose_free_text_query(
                postcode=postcode,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                county=county,
                country=country,
                query=query,
            )
            return ResolvedAddress(
                place_id=place_id,
                display_name=display_name or "Selected location",
                formatted_address=display_name or "Selected location",
                lat=float(lat),
                lon=float(lon),
                postcode=normalize_postcode(postcode),
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                county=county,
                country=country or settings.geocode_default_country,
                source="postcoder",
                confidence=1.0,
            )

        if place_id:
            return await cls.lookup_place(
                place_id,
                display_name=formatted_address,
                postcode=postcode,
            )

        query_text = compose_free_text_query(
            postcode=postcode,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            county=county,
            country=country,
            formatted_address=formatted_address,
            query=query,
        )

        results = await cls.search(query_text, limit=1)
        if not results:
            raise GeocodingError("No address match found")
        return results[0]