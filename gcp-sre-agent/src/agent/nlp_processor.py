# nlp_processor.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import re
from google.cloud import aiplatform
from datetime import datetime, timedelta


class QueryIntent(Enum):
    HEALTH_CHECK = "health_check"
    ERROR_ANALYSIS = "error_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    COST_ANALYSIS = "cost_analysis"
    SECURITY_AUDIT = "security_audit"
    CAPACITY_PLANNING = "capacity_planning"
    INCIDENT_INVESTIGATION = "incident_investigation"


@dataclass
class QueryContext:
    intent: QueryIntent
    time_range: str
    filters: Dict[str, Any]
    metrics: List[str]
    regions: Optional[List[str]] = None
    clusters: Optional[List[str]] = None


class SREQueryProcessor:
    def __init__(self, model_endpoint: str):
        self.model_endpoint = model_endpoint
        self.intent_patterns = self._initialize_intent_patterns()

    def _initialize_intent_patterns(self) -> Dict[QueryIntent, List[str]]:
        return {
            QueryIntent.HEALTH_CHECK: [
                r"health", r"status", r"running", r"alive", r"up"
            ],
            QueryIntent.ERROR_ANALYSIS: [
                r"error", r"exception", r"fail", r"4\d\d", r"5\d\d"
            ],
            QueryIntent.PERFORMANCE_METRICS: [
                r"performance", r"latency", r"cpu", r"memory", r"network"
            ],
            QueryIntent.COST_ANALYSIS: [
                r"cost", r"spend", r"budget", r"billing", r"expense"
            ],
            QueryIntent.SECURITY_AUDIT: [
                r"security", r"vulnerability", r"threat", r"compliance"
            ],
            QueryIntent.CAPACITY_PLANNING: [
                r"capacity", r"scaling", r"growth", r"forecast"
            ],
            QueryIntent.INCIDENT_INVESTIGATION: [
                r"incident", r"issue", r"problem", r"investigation"
            ]
        }

    def parse_time_range(self, query: str) -> str:
        time_patterns = {
            r"last (\d+) hour": "{}h",
            r"last (\d+) day": "{}d",
            r"last (\d+) minute": "{}m",
            r"past (\d+) hour": "{}h",
            r"past (\d+) day": "{}d",
            r"past (\d+) minute": "{}m"
        }

        for pattern, format_str in time_patterns.items():
            match = re.search(pattern, query)
            if match:
                return format_str.format(match.group(1))

        return "1h"  # default to last hour

    def extract_regions(self, query: str) -> Optional[List[str]]:
        region_pattern = r"(us|europe|asia)[-](east|west|central|south|north)[-]\d"
        return list(set(re.findall(region_pattern, query)))

    def extract_metrics(self, query: str) -> List[str]:
        metric_patterns = {
            "cpu": r"cpu|processor",
            "memory": r"memory|ram",
            "network": r"network|bandwidth|throughput",
            "disk": r"disk|storage|io",
            "latency": r"latency|response time",
            "errors": r"error|exception|failure"
        }

        metrics = []
        for metric, pattern in metric_patterns.items():
            if re.search(pattern, query.lower()):
                metrics.append(metric)

        return metrics or ["all"]

    async def process_query(self, query: str) -> QueryContext:
        # Detect primary intent
        intent = self._detect_intent(query)

        # Extract time range
        time_range = self.parse_time_range(query)

        # Extract regions if specified
        regions = self.extract_regions(query)

        # Extract metrics
        metrics = self.extract_metrics(query)

        # Build filters
        filters = self._build_filters(query)

        return QueryContext(
            intent=intent,
            time_range=time_range,
            filters=filters,
            metrics=metrics,
            regions=regions
        )

    def _detect_intent(self, query: str) -> QueryIntent:
        query_lower = query.lower()
        scores = {intent: 0 for intent in QueryIntent}

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 1

        return max(scores.items(), key=lambda x: x[1])[0]

    def _build_filters(self, query: str) -> Dict[str, Any]:
        filters = {}

        # Extract severity levels
        if re.search(r"(critical|high|medium|low)", query, re.I):
            severity = re.search(
                r"(critical|high|medium|low)", query, re.I).group(1)
            filters["severity"] = severity

        # Extract specific services
        services_pattern = r"(kubernetes|gke|compute|cloud run|cloud functions)"
        services = re.findall(services_pattern, query, re.I)
        if services:
            filters["services"] = services

        # Extract specific error codes
        error_codes = re.findall(r"([45]\d{2})", query)
        if error_codes:
            filters["error_codes"] = error_codes

        return filters

    async def get_response_template(self, context: QueryContext) -> Dict[str, Any]:
        templates = {
            QueryIntent.HEALTH_CHECK: {
                "title": "System Health Status",
                "metrics": ["availability", "uptime", "health_score"],
                "visualization": "status_dashboard"
            },
            QueryIntent.ERROR_ANALYSIS: {
                "title": "Error Analysis",
                "metrics": ["error_rate", "error_count", "error_distribution"],
                "visualization": "error_chart"
            },
            QueryIntent.PERFORMANCE_METRICS: {
                "title": "Performance Overview",
                "metrics": ["latency", "throughput", "resource_utilization"],
                "visualization": "performance_graphs"
            }
        }

        template = templates.get(context.intent, {
            "title": "Generic Response",
            "metrics": context.metrics,
            "visualization": "default_view"
        })

        return {
            **template,
            "time_range": context.time_range,
            "filters": context.filters,
            "regions": context.regions,
            "timestamp": datetime.now().isoformat()
        }
