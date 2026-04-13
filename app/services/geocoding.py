from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    source: str = 'google'
    confidence: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'place_id': self.place_id,
            'display_name': self.display_name,
            'formatted_address': self.formatted_address,
            'lat': self.lat,
            'lon': self.lon,
            'postcode': self.postcode,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'county': self.county,
            'country': self.country,
            'source': self.source,
            'confidence': self.confidence,
        }


def normalize_postcode(value: str | None) -> str | None:
    if not value:
        return None
    compact = ' '.join(value.upper().strip().split())
    return compact or None


def postcode_sector_from_postcode(postcode: str | None) -> str | None:
    postcode = normalize_postcode(postcode)
    if not postcode:
        return None
    parts = postcode.split()
    if not parts:
        return None
    outward = parts[0]
    inward = parts[1] if len(parts) > 1 else ''
    if not inward:
        return outward
    return f'{outward} {inward[0]}'


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
    parts = [address_line_1, address_line_2, city, county, postcode, country or settings.geocode_default_country]
    return ', '.join([p.strip() for p in parts if p and p.strip()])


def _pick_house_or_road(address: dict[str, Any]) -> str | None:
    street_number = address.get('street_number') or address.get('premise') or address.get('subpremise')
    route = address.get('route') or address.get('street_address')
    if street_number and route:
        return f'{street_number} {route}'
    return route or street_number


def _secondary_line(address: dict[str, Any]) -> str | None:
    for key in ('sublocality_level_1', 'sublocality', 'neighborhood', 'premise', 'subpremise'):
        if address.get(key):
            return address[key]
    return None


def _google_component_map(components: list[dict[str, Any]]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for component in components:
        long_name = component.get('longText') or component.get('long_name') or component.get('longName')
        if not long_name:
            continue
        types = component.get('types') or []
        for t in types:
            mapped[t] = long_name
    return mapped


def _address_from_google_components(components: list[dict[str, Any]]) -> dict[str, str | None]:
    mapped = _google_component_map(components)
    street_number = mapped.get('street_number')
    route = mapped.get('route')
    address_line_1 = ' '.join(part for part in [street_number, route] if part).strip() or None
    city = (
        mapped.get('postal_town')
        or mapped.get('locality')
        or mapped.get('administrative_area_level_2')
        or mapped.get('sublocality_level_1')
    )
    county = mapped.get('administrative_area_level_2') or mapped.get('administrative_area_level_1')
    country = mapped.get('country') or settings.geocode_default_country
    return {
        'postcode': normalize_postcode(mapped.get('postal_code')),
        'address_line_1': address_line_1,
        'address_line_2': _secondary_line(mapped),
        'city': city,
        'county': county,
        'country': country,
    }


def _secondary_line(mapped: dict[str, str]) -> str | None:
    for key in ('subpremise', 'premise', 'sublocality_level_1', 'sublocality', 'neighborhood'):
        if mapped.get(key):
            return mapped[key]
    return None


def _resolved_from_google_geocode(item: dict[str, Any]) -> ResolvedAddress:
    components = item.get('addressComponents') or []
    parts = _address_from_google_components(components)
    location = item.get('location') or item.get('geometry', {}).get('location') or {}
    lat = location.get('latitude') if 'latitude' in location else location.get('lat')
    lon = location.get('longitude') if 'longitude' in location else location.get('lng')
    formatted_address = item.get('formattedAddress') or item.get('formatted_address') or ''
    place_id = item.get('placeId') or item.get('place_id')
    granularity = str(item.get('granularity') or '').upper()
    confidence = 1.0 if granularity == 'ROOFTOP' else 0.9 if granularity else None
    return ResolvedAddress(
        place_id=place_id,
        display_name=formatted_address,
        formatted_address=formatted_address,
        lat=float(lat),
        lon=float(lon),
        postcode=parts['postcode'],
        address_line_1=parts['address_line_1'],
        address_line_2=parts['address_line_2'],
        city=parts['city'],
        county=parts['county'],
        country=parts['country'],
        source='google',
        confidence=confidence,
    )


class GeocodingService:
    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            'User-Agent': settings.geocode_user_agent,
            'Accept-Language': settings.geocode_accept_language,
            'Referer': settings.app_base_url,
            'Accept': 'application/json',
        }

    @staticmethod
    def _looks_like_postcode(value: str) -> bool:
        value = normalize_postcode(value) or ''
        return len(value.replace(' ', '')) >= 5

    @staticmethod
    def _provider() -> str:
        return (settings.geocode_provider or 'google').strip().lower()

    @classmethod
    async def _request_ideal(cls, path: str, *, params: dict[str, Any] | None = None) -> Any:
        if not settings.geocode_api_key:
            raise GeocodingError('GEOCODE_API_KEY is not configured')

        base = settings.geocode_base_url.rstrip('/')
        query = dict(params or {})
        query['api-key'] = settings.geocode_api_key

        async with httpx.AsyncClient(timeout=settings.geocode_timeout_seconds, headers=cls._headers()) as client:
            res = await client.get(f'{base}{path}', params=query)
            if res.status_code >= 400:
                raise GeocodingError(f'Geocoding request failed: {res.status_code}')
            return res.json()

    @classmethod
    async def _google_autocomplete(cls, q: str, *, limit: int) -> list[dict[str, Any]]:
        if not settings.geocode_api_key:
            raise GeocodingError('GEOCODE_API_KEY is not configured')

        body: dict[str, Any] = {
            'input': q,
            'includedRegionCodes': [code.strip().lower() for code in settings.geocode_country_codes.split(',') if code.strip()],
        }
        headers = {
            **cls._headers(),
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': settings.geocode_api_key,
            'X-Goog-FieldMask': 'suggestions.placePrediction.place,suggestions.placePrediction.placeId,suggestions.placePrediction.text',
        }
        async with httpx.AsyncClient(timeout=settings.geocode_timeout_seconds, headers=headers) as client:
            res = await client.post('https://places.googleapis.com/v1/places:autocomplete', json=body)
            if res.status_code >= 400:
                raise GeocodingError(f'Geocoding request failed: {res.status_code}')
            suggestions = res.json().get('suggestions') or []
        return suggestions[:limit]

    @classmethod
    async def _google_geocode_place_id(cls, place_id: str) -> ResolvedAddress:
        if not settings.geocode_api_key:
            raise GeocodingError('GEOCODE_API_KEY is not configured')

        headers = {
            **cls._headers(),
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': settings.geocode_api_key,
            'X-Goog-FieldMask': 'placeId,formattedAddress,location,addressComponents,granularity',
        }
        url = f'https://geocode.googleapis.com/v4/geocode/places/{place_id}'
        async with httpx.AsyncClient(timeout=settings.geocode_timeout_seconds, headers=headers) as client:
            res = await client.get(url)
            if res.status_code >= 400:
                raise GeocodingError(f'Geocoding request failed: {res.status_code}')
            payload = res.json()
        return _resolved_from_google_geocode(payload)

    @classmethod
    async def _google_geocode_text(cls, query: str) -> list[ResolvedAddress]:
        if not settings.geocode_api_key:
            raise GeocodingError('GEOCODE_API_KEY is not configured')

        headers = {
            **cls._headers(),
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': settings.geocode_api_key,
            'X-Goog-FieldMask': 'results.placeId,results.formattedAddress,results.location,results.addressComponents,results.granularity',
        }
        params = {'address': query, 'regionCode': settings.geocode_country_codes.split(',')[0].strip().upper() or 'GB'}
        async with httpx.AsyncClient(timeout=settings.geocode_timeout_seconds, headers=headers) as client:
            res = await client.get('https://geocode.googleapis.com/v4beta/geocode/address', params=params)
            if res.status_code >= 400:
                raise GeocodingError(f'Geocoding request failed: {res.status_code}')
            payload = res.json()
        return [_resolved_from_google_geocode(item) for item in (payload.get('results') or [])]

    @staticmethod
    def _from_provider_address(item: dict[str, Any], *, place_id: str | None = None, display_name: str | None = None) -> ResolvedAddress:
        formatted = item.get('formatted_address')
        if isinstance(formatted, list):
            formatted_address = ', '.join([str(x).strip() for x in formatted if str(x).strip()])
        else:
            formatted_address = str(formatted or display_name or '').strip()

        lat = item.get('latitude') or item.get('lat')
        lon = item.get('longitude') or item.get('lon')

        address_line_1 = (
            item.get('line_1')
            or item.get('address_line_1')
            or item.get('thoroughfare')
            or item.get('line1')
        )
        address_line_2 = (
            item.get('line_2')
            or item.get('address_line_2')
            or item.get('line2')
            or item.get('locality')
        )

        city = item.get('town_or_city') or item.get('city')
        county = item.get('county')
        postcode = normalize_postcode(item.get('postcode'))
        country = item.get('country') or settings.geocode_default_country

        return ResolvedAddress(
            place_id=place_id,
            display_name=display_name or formatted_address,
            formatted_address=formatted_address,
            lat=float(lat),
            lon=float(lon),
            postcode=postcode,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            county=county,
            country=country,
            source='ideal_compat',
            confidence=1.0,
        )

    @classmethod
    async def search(cls, q: str, *, limit: int | None = None) -> list[ResolvedAddress]:
        query = (q or '').strip()
        if not query:
            return []

        limit = max(1, min(limit or settings.geocode_limit, 10))
        provider = cls._provider()

        if provider == 'google':
            suggestions = await cls._google_autocomplete(query, limit=limit)
            results: list[ResolvedAddress] = []
            for item in suggestions:
                pred = item.get('placePrediction') or {}
                place_id = pred.get('placeId') or pred.get('place', '').split('/')[-1]
                if not place_id:
                    continue
                try:
                    results.append(await cls._google_geocode_place_id(place_id))
                except GeocodingError:
                    continue
            if results:
                return results[:limit]
            return (await cls._google_geocode_text(query))[:limit]

        if provider != 'ideal_compat':
            raise GeocodingError(f'Unsupported geocode provider: {settings.geocode_provider}')

        if cls._looks_like_postcode(query):
            payload = await cls._request_ideal(f'/find/{query}', params={'expand': 'true'})
            addresses = payload.get('addresses') or []
            return [
                cls._from_provider_address(item, place_id=f'postcode:{idx + 1}')
                for idx, item in enumerate(addresses[:limit])
            ]

        payload = await cls._request_ideal(f'/autocomplete/{query}')
        suggestions = payload.get('suggestions') or []
        results: list[ResolvedAddress] = []
        for item in suggestions[:limit]:
            suggestion_id = str(item.get('id'))
            suggestion_label = item.get('address') or query
            full = await cls.lookup_place(suggestion_id, display_name=suggestion_label)
            results.append(full)
        return results

    @classmethod
    async def lookup_place(cls, place_id: str, display_name: str | None = None) -> ResolvedAddress:
        provider = cls._provider()
        if provider == 'google':
            return await cls._google_geocode_place_id(place_id)
        payload = await cls._request_ideal(f'/get/{place_id}')
        return cls._from_provider_address(payload, place_id=place_id, display_name=display_name)

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
        provider = cls._provider()
        manual_source = 'google' if provider == 'google' else 'ideal_compat'

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
                display_name=display_name or 'Selected location',
                formatted_address=display_name or 'Selected location',
                lat=float(lat),
                lon=float(lon),
                postcode=normalize_postcode(postcode),
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                county=county,
                country=country or settings.geocode_default_country,
                source=manual_source,
                confidence=1.0,
            )

        if place_id:
            return await cls.lookup_place(place_id, display_name=formatted_address)

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
            raise GeocodingError('No address match found')
        return results[0]
