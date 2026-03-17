from pydantic import BaseModel


class OpsSummaryOut(BaseModel):
    total_bins: int
    active_bins: int
    inactive_bins: int
    critical_bins: int
    warning_bins: int
    healthy_bins: int
    stale_bins: int
    open_alerts: int
    critical_alerts: int
    latest_ddss_run_id: int | None = None
    latest_route_plan_id: int | None = None
    avg_fill_level: float
    avg_predicted_fill_6h: float