from google.cloud import logging
from google.cloud import aiplatform
import vertexai
from vertexai.language_models import TextGenerationModel
import asyncio
from datetime import datetime, timedelta
import json
import logging as python_logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ErrorLogEntry:
    """Structure for error log entries"""
    timestamp: datetime
    severity: str
    message: str
    resource: Dict[str, Any]
    labels: Dict[str, Any]
    trace: Optional[str]
    source_location: Optional[Dict[str, Any]]
    operation: Optional[Dict[str, Any]]

class StackdriverAIAgent:
    """
    AI-powered Stackdriver log monitoring agent that watches for errors,
    analyzes them, and provides intelligent summaries and recommendations.
    """

    def __init__(self, project_id: str, location: str = "us-central1"):
        """
        Initialize the Stackdriver AI Agent
        
        Args:
            project_id: GCP project ID
            location: GCP location for Vertex AI
        """
        # Initialize Stackdriver logging client
        self.logging_client = logging.Client(project=project_id)
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = TextGenerationModel.from_pretrained("gemini-pro")
        
        # Setup logging
        self.logger = python_logging.getLogger(__name__)
        
        # Initialize error patterns storage
        self.error_patterns = defaultdict(int)
        self.last_analyzed = datetime.now()

    async def watch_error_logs(self, interval_seconds: int = 300):
        """
        Continuously watch Stackdriver logs for errors
        
        Args:
            interval_seconds: Interval between log checks in seconds
        """
        while True:
            try:
                # Fetch and analyze logs
                analysis = await self.analyze_recent_errors()
                if analysis:
                    self.logger.info(f"Log Analysis:\n{analysis}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error watching logs: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

    async def analyze_recent_errors(self, lookback_minutes: int = 15) -> Optional[str]:
        """
        Analyze recent error logs and provide insights
        
        Args:
            lookback_minutes: How far back to look for logs
            
        Returns:
            str: AI-generated analysis of error logs
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=lookback_minutes)
            
            # Construct filter for error and higher severity logs
            filter_str = f"""
                timestamp >= "{start_time.isoformat()}Z"
                AND timestamp <= "{end_time.isoformat()}Z"
                AND severity >= ERROR
            """
            
            # Fetch logs
            logs = self.logging_client.list_entries(
                filter_=filter_str,
                order_by="timestamp desc"
            )
            
            # Process logs
            error_entries = []
            for entry in logs:
                error_entry = ErrorLogEntry(
                    timestamp=entry.timestamp,
                    severity=entry.severity,
                    message=entry.payload.get('message', str(entry.payload)),
                    resource=entry.resource.to_api_repr(),
                    labels=entry.labels,
                    trace=entry.trace,
                    source_location=entry.source_location,
                    operation=entry.operation
                )
                error_entries.append(error_entry)
            
            if not error_entries:
                return None
                
            # Update error patterns
            self._update_error_patterns(error_entries)
            
            # Generate analysis
            return await self._generate_error_analysis(error_entries)
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {str(e)}")
            return f"Error analysis failed: {str(e)}"

    def _update_error_patterns(self, entries: List[ErrorLogEntry]):
        """
        Update tracked error patterns
        
        Args:
            entries: List of error log entries
        """
        for entry in entries:
            # Create pattern key from relevant fields
            pattern_key = (
                entry.severity,
                entry.resource.get('type'),
                self._extract_error_type(entry.message)
            )
            self.error_patterns[pattern_key] += 1

    async def _generate_error_analysis(self, entries: List[ErrorLogEntry]) -> str:
        """
        Generate AI analysis of error logs
        
        Args:
            entries: List of error log entries
            
        Returns:
            str: AI-generated analysis
        """
        # Prepare data for analysis
        analysis_data = {
            "error_entries": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "severity": entry.severity,
                    "message": entry.message,
                    "resource": entry.resource,
                    "labels": entry.labels
                } for entry in entries
            ],
            "error_patterns": [
                {
                    "severity": severity,
                    "resource_type": resource_type,
                    "error_type": error_type,
                    "count": count
                }
                for (severity, resource_type, error_type), count 
                in self.error_patterns.items()
            ],
            "time_range": {
                "start": min(entry.timestamp for entry in entries).isoformat(),
                "end": max(entry.timestamp for entry in entries).isoformat()
            }
        }
        
        analysis_prompt = """
        Analyze these Stackdriver error logs and provide insights:
        {data}
        
        Include:
        1. Summary of error patterns and trends
        2. Critical issues requiring immediate attention
        3. Common error types and their frequency
        4. Potential root causes
        5. Recommended actions
        6. Service impact assessment
        
        Focus on actionable insights and prioritize by severity.
        """
        
        analysis = await self.model.predict(
            analysis_prompt.format(data=json.dumps(analysis_data, indent=2))
        )
        return analysis.text

    def _extract_error_type(self, message: str) -> str:
        """
        Extract error type from message
        
        Args:
            message: Error message
            
        Returns:
            str: Extracted error type
        """
        # Add logic to extract error type from message
        # This could be enhanced with regex patterns or ML-based classification
        return message.split()[0] if message else "Unknown"

    async def get_error_summary(self, hours: int = 24) -> str:
        """
        Get summary of errors over specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            str: AI-generated error summary
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Fetch logs
            filter_str = f"""
                timestamp >= "{start_time.isoformat()}Z"
                AND severity >= ERROR
            """
            
            logs = self.logging_client.list_entries(
                filter_=filter_str,
                order_by="timestamp desc"
            )
            
            # Process and categorize errors
            errors_by_service = defaultdict(list)
            errors_by_severity = defaultdict(list)
            
            for entry in logs:
                service = entry.resource.type
                errors_by_service[service].append(entry)
                errors_by_severity[entry.severity].append(entry)
            
            # Prepare summary data
            summary_data = {
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "by_service": {
                    service: [
                        {
                            "timestamp": entry.timestamp.isoformat(),
                            "severity": entry.severity,
                            "message": entry.payload.get('message', str(entry.payload))
                        } for entry in entries
                    ]
                    for service, entries in errors_by_service.items()
                },
                "by_severity": {
                    severity: len(entries)
                    for severity, entries in errors_by_severity.items()
                }
            }
            
            summary_prompt = f"""
            Generate a comprehensive summary of these error logs:
            {json.dumps(summary_data, indent=2)}
            
            Include:
            1. Overall error count and distribution
            2. Most affected services
            3. Critical error patterns
            4. Trending issues
            5. Service health assessment
            6. Key recommendations
            
            Format the summary in a clear, actionable way.
            """
            
            summary = await self.model.predict(summary_prompt)
            return summary.text
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

class StackdriverErrorMonitor:
    """
    High-level interface for Stackdriver error monitoring
    """
    
    def __init__(self, project_id: str):
        self.agent = StackdriverAIAgent(project_id)
        self.logger = python_logging.getLogger(__name__)

    async def start_monitoring(self, interval_seconds: int = 300):
        """Start continuous error monitoring"""
        try:
            self.logger.info("Starting Stackdriver error monitoring...")
            await self.agent.watch_error_logs(interval_seconds)
        except Exception as e:
            self.logger.error(f"Monitoring failed: {str(e)}")
            raise

    async def get_current_status(self) -> str:
        """Get current error status summary"""
        try:
            return await self.agent.get_error_summary(hours=1)
        except Exception as e:
            self.logger.error(f"Status check failed: {str(e)}")
            return f"Status check failed: {str(e)}"

def main():
    """Main function to run the monitor"""
    project_id = "your-project-id"
    monitor = StackdriverErrorMonitor(project_id)
    
    # Run the monitoring loop
    asyncio.run(monitor.start_monitoring())

if __name__ == "__main__":
    main()
