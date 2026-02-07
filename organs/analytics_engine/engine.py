"""
Analytics Engine Core Logic
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import statistics

log = logging.getLogger(__name__)


class MetricType(Enum):
    THREAT_COUNT = "threat_count"
    ANOMALY_SCORE = "anomaly_score"
    LOGIN_ATTEMPTS = "login_attempts"
    FAILED_AUTHS = "failed_auths"
    SESSIONS_ACTIVE = "sessions_active"
    ALERTS_GENERATED = "alerts_generated"
    RESPONSE_TIME = "response_time"
    BLOCKED_IPS = "blocked_ips"


@dataclass
class AnalyticsConfig:
    AGGREGATION_INTERVAL_SECONDS: int = 60
    RETENTION_HOURS: int = 168
    TREND_WINDOW_HOURS: int = 24
    ALERT_THRESHOLD_MULTIPLIER: float = 2.0


@dataclass
class SecurityMetric:
    metric_type: MetricType
    value: float
    timestamp: datetime
    source: str = "system"
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ThreatTrend:
    metric_type: MetricType
    period_start: datetime
    period_end: datetime
    average: float
    minimum: float
    maximum: float
    std_dev: float
    trend_direction: str
    data_points: int


@dataclass
class AnalyticsReport:
    generated_at: datetime
    period_hours: int
    total_threats: int
    total_anomalies: int
    total_blocked: int
    threat_trends: List[ThreatTrend]
    top_sources: List[Dict]
    risk_score: float


class AnalyticsEngine:
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self._metrics: List[SecurityMetric] = []
        self._aggregated: Dict[MetricType, List[float]] = defaultdict(list)
        self._reports: List[AnalyticsReport] = []

    def record_metric(self, metric_type: MetricType, value: float, source: str = "system", tags: Dict = None):
        metric = SecurityMetric(metric_type=metric_type, value=value, timestamp=datetime.utcnow(), source=source, tags=tags or {})
        self._metrics.append(metric)
        self._aggregated[metric_type].append(value)
        self._prune_old_data()

    def _prune_old_data(self):
        cutoff = datetime.utcnow() - timedelta(hours=self.config.RETENTION_HOURS)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]

    def calculate_trend(self, metric_type: MetricType, hours: int = None) -> Optional[ThreatTrend]:
        hours = hours or self.config.TREND_WINDOW_HOURS
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        values = [m.value for m in self._metrics if m.metric_type == metric_type and m.timestamp > cutoff]
        if len(values) < 2:
            return None
        avg = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        mid = len(values) // 2
        first_half = statistics.mean(values[:mid]) if mid > 0 else avg
        second_half = statistics.mean(values[mid:]) if mid > 0 else avg
        if second_half > first_half * 1.1:
            direction = "increasing"
        elif second_half < first_half * 0.9:
            direction = "decreasing"
        else:
            direction = "stable"
        return ThreatTrend(metric_type=metric_type, period_start=cutoff, period_end=datetime.utcnow(),
                          average=avg, minimum=min(values), maximum=max(values), std_dev=std,
                          trend_direction=direction, data_points=len(values))

    def generate_report(self, hours: int = 24) -> AnalyticsReport:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [m for m in self._metrics if m.timestamp > cutoff]
        threats = sum(1 for m in recent if m.metric_type == MetricType.THREAT_COUNT)
        anomalies = sum(1 for m in recent if m.metric_type == MetricType.ANOMALY_SCORE and m.value > 0.7)
        blocked = sum(int(m.value) for m in recent if m.metric_type == MetricType.BLOCKED_IPS)
        trends = [t for t in (self.calculate_trend(mt, hours) for mt in MetricType) if t]
        source_counts = defaultdict(int)
        for m in recent:
            source_counts[m.source] += 1
        top_sources = [{"source": k, "count": v} for k, v in sorted(source_counts.items(), key=lambda x: -x[1])[:10]]
        risk = min(100, (threats * 5) + (anomalies * 10) + (blocked * 2))
        report = AnalyticsReport(generated_at=datetime.utcnow(), period_hours=hours, total_threats=threats,
                                 total_anomalies=anomalies, total_blocked=blocked, threat_trends=trends,
                                 top_sources=top_sources, risk_score=risk)
        self._reports.append(report)
        return report

    def get_stats(self) -> Dict:
        return {"total_metrics": len(self._metrics), "metric_types": len(self._aggregated),
                "reports_generated": len(self._reports),
                "oldest_data": self._metrics[0].timestamp.isoformat() if self._metrics else None}
