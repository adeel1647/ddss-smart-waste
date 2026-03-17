from pydantic import BaseModel


class AnalyticsOverviewOut(BaseModel):
    avg_fill_today: float
    max_fill_today: float
    critical_alerts_today: int
    open_alerts_total: int
    latest_route_distance_km: float
    top_waste_class_today: str | None = None


class TrendPoint(BaseModel):
    ts: str
    value: float


class FillTrendResponse(BaseModel):
    points: list[TrendPoint]


class ClassDistributionItem(BaseModel):
    label: str
    count: int


class ClassDistributionResponse(BaseModel):
    items: list[ClassDistributionItem]