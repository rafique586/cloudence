from google.cloud import logging
from google.cloud import aiplatform
from google.cloud import monitoring_v3
import vertexai
from vertexai.language_models import TextGenerationModel
import asyncio
from datetime import datetime, timedelta
import json
import logging as python_logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re
import numpy as np
from enum import Enum
import aiohttp
import yaml

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class ErrorPattern:
    """Structure for identified error patterns"""
    pattern_id: str
    pattern_type: str
    regex: str
    severity: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    affected_services: Set[str]
    sample_messages: List[str]
    possible_causes: List[str]
    recommended_actions: List[str]

@dataclass
class ServiceHealth:
    """Structure for service health status"""
    service_name: str
    error_rate: float
    error_count: int
    latency_p95: float
    availability: float
    last_error: datetime
    status: str
    issues: List[str]

class AlertConfig:
    """Alert configuration settings"""
    def __init__(self, config_file: str = "alert_config.yaml"):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.thresholds = self.config.get('thresholds', {})
        self.notification_channels = self.config.get('notification_channels', [])
        self.alert_rules = self.config.get('alert_rules', {})

class AdvancedStackdriverAIAgent:
    """
    Enhanced AI-powered Stackdriver monitoring agent with advanced pattern detection,
    service monitoring, and intelligent alerting capabilities.
    """

    def __init__(self, 
                 project_id: str, 
                 location: str = "us-central1",
                 alert_config: str = "alert_config.yaml"):
        """
        Initialize the advanced Stackdriver AI Agent
        
        Args:
            project_id: GCP project ID
            location: GCP location for Vertex AI
            alert_config: Path to alert configuration file
        """
        # Initialize clients
        self.project_id = project_id
        self.logging_client = logging.Client(project=project_id)
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = TextGenerationModel.from_pretrained("gemini-pro")
        
        # Setup logging
        self.logger = python_logging.getLogger(__name__)
        
        # Initialize pattern detection
        self.error_patterns = {}
        self.pattern_matcher = ErrorPatternMatcher()
        
        # Initialize service monitoring
        self.service_health = {}
        self.service_monitor = ServiceMonitor(project_id)
        
        # Initialize alert system
        self.alert_config = AlertConfig(alert_config)
        self.alert_manager = AlertManager(self.alert_config)
        
        # Initialize analysis cache
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def monitor_services(self):
        """
        Continuously monitor services and detect issues
        """
        while True:
            try:
                # Update service health status
                service_status = await self.service_monitor.update_health()
                
                # Analyze service health
                analysis = await self._analyze_service_health(service_status)
                
                # Generate alerts if needed
                await self.alert_manager.process_service_health(service_status, analysis)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Service monitoring error: {str(e)}")
                await asyncio.sleep(60)

    async def detect_error_patterns(self, entries: List[ErrorLogEntry]) -> List[ErrorPattern]:
        """
        Advanced error pattern detection using ML and heuristics
        """
        try:
            # Group similar errors
            grouped_errors = self.pattern_matcher.group_similar_errors(entries)
            
            # Analyze each group
            patterns = []
            for group in grouped_errors:
                pattern = await self._analyze_error_group(group)
                if pattern:
                    patterns.append(pattern)
                    
                    # Update pattern database
                    self.error_patterns[pattern.pattern_id] = pattern
            
            # Identify new patterns
            new_patterns = self._identify_new_patterns(patterns)
            
            # Generate alerts for new patterns
            if new_patterns:
                await self.alert_manager.process_new_patterns(new_patterns)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Pattern detection error: {str(e)}")
            return []

    async def _analyze_error_group(self, group: List[ErrorLogEntry]) -> Optional[ErrorPattern]:
        """
        Analyze a group of similar errors to identify patterns
        """
        try:
            # Extract common elements
            messages = [entry.message for entry in group]
            services = {entry.resource.get('type') for entry in group}
            
            # Generate pattern signature
            pattern_signature = self.pattern_matcher.generate_signature(messages)
            
            # Use AI to analyze pattern
            analysis_prompt = f"""
            Analyze these error messages and identify the pattern:
            Messages: {json.dumps(messages[:5])}  # Sample of messages
            Services: {list(services)}
            Pattern Signature: {pattern_signature}
            
            Provide:
            1. Pattern type/category
            2. Possible root causes
            3. Recommended actions
            4. Severity assessment
            5. Regex pattern to match similar errors
            """
            
            analysis = await self.model.predict(analysis_prompt)
            analysis_data = json.loads(analysis.text)
            
            return ErrorPattern(
                pattern_id=f"PATTERN-{hash(pattern_signature)}",
                pattern_type=analysis_data['pattern_type'],
                regex=analysis_data['regex_pattern'],
                severity=analysis_data['severity'],
                frequency=len(group),
                first_seen=min(entry.timestamp for entry in group),
                last_seen=max(entry.timestamp for entry in group),
                affected_services=services,
                sample_messages=messages[:5],
                possible_causes=analysis_data['possible_causes'],
                recommended_actions=analysis_data['recommended_actions']
            )
            
        except Exception as e:
            self.logger.error(f"Error group analysis failed: {str(e)}")
            return None

    async def analyze_service_impact(self, error_patterns: List[ErrorPattern]) -> str:
        """
        Analyze service impact of detected error patterns
        """
        try:
            # Collect service metrics
            service_metrics = await self.service_monitor.get_service_metrics()
            
            # Prepare impact analysis data
            impact_data = {
                "error_patterns": [
                    {
                        "pattern_type": pattern.pattern_type,
                        "severity": pattern.severity,
                        "frequency": pattern.frequency,
                        "affected_services": list(pattern.affected_services),
                        "duration": (pattern.last_seen - pattern.first_seen).total_seconds()
                    }
                    for pattern in error_patterns
                ],
                "service_metrics": service_metrics
            }
            
            # Generate impact analysis
            analysis_prompt = f"""
            Analyze the service impact of these error patterns:
            {json.dumps(impact_data, indent=2)}
            
            Provide:
            1. Overall service health assessment
            2. Critical service impacts
            3. Performance degradation analysis
            4. Business impact assessment
            5. Mitigation recommendations
            6. Priority ordering of issues
            """
            
            analysis = await self.model.predict(analysis_prompt)
            return analysis.text
            
        except Exception as e:
            self.logger.error(f"Service impact analysis failed: {str(e)}")
            return f"Impact analysis failed: {str(e)}"

    async def generate_alerts(self, 
                            patterns: List[ErrorPattern], 
                            service_health: Dict[str, ServiceHealth]) -> List[Dict]:
        """
        Generate intelligent alerts based on patterns and service health
        """
        try:
            alerts = []
            
            # Process error patterns
            for pattern in patterns:
                if self._should_alert_pattern(pattern):
                    alert = await self._create_pattern_alert(pattern)
                    alerts.append(alert)
            
            # Process service health
            for service_name, health in service_health.items():
                if self._should_alert_service(health):
                    alert = await self._create_service_alert(health)
                    alerts.append(alert)
            
            # Deduplicate and prioritize alerts
            unique_alerts = self._deduplicate_alerts(alerts)
            prioritized_alerts = self._prioritize_alerts(unique_alerts)
            
            # Send alerts
            await self.alert_manager.send_alerts(prioritized_alerts)
            
            return prioritized_alerts
            
        except Exception as e:
            self.logger.error(f"Alert generation failed: {str(e)}")
            return []

    def _should_alert_pattern(self, pattern: ErrorPattern) -> bool:
        """
        Determine if an error pattern should trigger an alert
        """
        # Check against alert rules
        rules = self.alert_config.alert_rules.get('patterns', {})
        
        # Check frequency threshold
        if pattern.frequency >= rules.get('frequency_threshold', 10):
            return True
            
        # Check severity
        if pattern.severity in rules.get('alert_severities', ['CRITICAL', 'HIGH']):
            return True
            
        # Check for rapid increase
        if self._is_pattern_increasing(pattern):
            return True
            
        return False

    def _should_alert_service(self, health: ServiceHealth) -> bool:
        """
        Determine if service health should trigger an alert
        """
        rules = self.alert_config.alert_rules.get('services', {})
        
        # Check error rate threshold
        if health.error_rate >= rules.get('error_rate_threshold', 0.05):
            return True
            
        # Check availability threshold
        if health.availability <= rules.get('availability_threshold', 0.99):
            return True
            
        # Check latency threshold
        if health.latency_p95 >= rules.get('latency_threshold', 1000):
            return True
            
        return False

    def _prioritize_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """
        Prioritize alerts based on severity and impact
        """
        # Calculate priority score for each alert
        scored_alerts = []
        for alert in alerts:
            score = self._calculate_alert_priority(alert)
            scored_alerts.append((score, alert))
            
        # Sort by priority score
        scored_alerts.sort(reverse=True)
        
        return [alert for _, alert in scored_alerts]

    def _calculate_alert_priority(self, alert: Dict) -> float:
        """
        Calculate priority score for an alert
        """
        # Base score from severity
        severity_scores = {
            'CRITICAL': 1.0,
            'HIGH': 0.8,
            'MEDIUM': 0.6,
            'LOW': 0.4,
            'INFO': 0.2
        }
        base_score = severity_scores.get(alert['severity'], 0.2)
        
        # Adjust for impact
        if 'impact_score' in alert:
            base_score *= (1 + alert['impact_score'])
            
        # Adjust for frequency/duration
        if 'frequency' in alert:
            base_score *= (1 + min(alert['frequency'] / 100, 1))
            
        # Adjust for service criticality
        if 'service' in alert:
            service_criticality = self.alert_config.config.get('service_criticality', {})
            criticality_multiplier = service_criticality.get(alert['service'], 1.0)
            base_score *= criticality_multiplier
            
        return base_score

class AlertManager:
    """
    Manages alert generation, deduplication, and delivery
    """
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.sent_alerts = {}  # Track sent alerts
        self.logger = python_logging.getLogger(__name__)

    async def send_alerts(self, alerts: List[Dict]):
        """
        Send alerts through configured channels
        """
        for alert in alerts:
            if not self._is_duplicate(alert):
                await self._send_to_channels(alert)
                self._record_sent_alert(alert)

    async def _send_to_channels(self, alert: Dict):
        """
        Send alert to all configured channels
        """
        for channel in self.config.notification_channels:
            try:
                if channel['type'] == 'slack':
                    await self._send_slack_alert(channel, alert)
                elif channel['type'] == 'email':
                    await self._send_email_alert(channel, alert)
                elif channel['type'] == 'pagerduty':
                    await self._send_pagerduty_alert(channel, alert)
            except Exception as e:
                self.logger.error(f"Error sending alert to {channel['type']}: {str(e)}")

    async def _send_slack_alert(self, channel: Dict, alert: Dict):
        """
        Send alert to Slack
        """
        webhook_url = channel['webhook_url']
        
        message = self._format_slack_message(alert)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status != 200:
                    raise Exception(f"Slack API error: {await response.text()}")

    def _format_slack_message(self, alert: Dict) -> Dict:
        """
        Format alert for Slack
        """
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {alert['severity']} Alert: {alert['title']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": alert['description']
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Impact:*\n{alert.get('impact', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Service:*\n{alert.get('service', 'Multiple')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommended Action:*\n{alert.get('recommended_action', 'Investigate issue')}"
                    }
                }
            ]
        }

def main():
    """Main function to run the enhanced monitoring system"""
    project_id = "your-project-id"
    agent = AdvancedStackdriverAIAgent(project_id)
    
    async def run_monitoring():
        # Start