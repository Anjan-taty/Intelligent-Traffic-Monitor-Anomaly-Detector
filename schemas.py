from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class RequestLogBase(BaseModel):
    ip_address: str
    method: str
    endpoint: str
    status_code: int
    response_time_ms: float
    user_agent: Optional[str] = None
    is_blocked: bool = False

class RequestLogCreate(RequestLogBase):
    pass

class RequestLogResponse(RequestLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime

class AnomalyAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ip_address: str
    threat_score: float
    anomaly_type: str
    reason: str
    metrics_snapshot: Optional[str] = None
    mitigation_status: str
    timestamp: datetime

class BlockedIPCreate(BaseModel):
    ip_address: str
    reason: str
    threat_level: str = "HIGH"
    duration_minutes: Optional[int] = 60

class BlockedIPResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ip_address: str
    reason: str
    threat_level: str
    blocked_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

class SystemStats(BaseModel):
    total_requests: int
    total_blocked: int
    active_threats: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    current_rps: float
    status_code_distribution: Dict[str, int]
    top_endpoints: List[Dict[str, Any]]
    recent_alerts: List[AnomalyAlertResponse]

class SimulationRequest(BaseModel):
    scenario: str = Field(..., description="human, scraper, ddos, or bruteforce")
    requests_count: int = Field(default=30, ge=1, le=500)
    concurrency: int = Field(default=5, ge=1, le=50)

class SimulationResponse(BaseModel):
    status: str
    scenario: str
    total_sent: int
    successful: int
    blocked: int
    duration_seconds: float