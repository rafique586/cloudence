import os
from datetime import datetime, timedelta
from google.cloud import monitoring_v3
from google.cloud import aiplatform
from vertexai.language_models import TextGenerationModel
import vertexai
import json
import logging

class GCPSREAgent:
    def __init__(self, project_id, location="us-central1"):
        """
        Initialize the SRE AI Agent with GCP credentials and project settings
        """
        self.project_id = project_id
        self.project_name = f"projects/{project_id}"
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = TextGenerationModel.from_pretrained("gemini-pro")
        
        # Initialize monitoring client
        self.client = monitoring_v3.MetricServiceClient()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_metric_data(self, metric_type, hours=1, alignment_period_seconds=300):
        """
        Fetch metric data from Cloud Monitoring
        """
        now = datetime.utcnow()
        seconds = hours * 3600
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(now.timestamp())},
                "start_time": {"seconds": int((now - timedelta(hours=hours)).timestamp())},
            }
        )

        aggregation = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": alignment_period_seconds},
                "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
            }
        )

        results = self.client.list_time_series(
            request={
                "name": self.project_name,
                "filter": f'metric.type = "{metric_type}"',
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation,
            }
        )
        
        return list(results)

    def analyze_metrics(self, metrics_data):
        """
        Analyze metrics using Gemini to provide insights and recommendations
        """
        metrics_context = self._format_metrics_for_analysis(metrics_data)
        
        prompt = f"""
        As an SRE expert, analyze the following metrics and provide:
        1. Key observations
        2. Potential issues or anomalies
        3. Recommended actions
        4. Performance optimization suggestions

        Metrics data:
        {metrics_context}
        """

        response = self.model.predict(prompt)
        return response.text

    def _format_metrics_for_analysis(self, metrics_data):
        """
        Format metrics data into a structured format for analysis
        """
        formatted_data = []
        for series in metrics_data:
            metric_data = {
                "metric_type": series.metric.type,
                "resource_type": series.resource.type,
                "points": [
                    {
                        "value": point.value.double_value,
                        "timestamp": point.interval.end_time.isoformat()
                    }
                    for point in series.points
                ]
            }
            formatted_data.append(metric_data)
        return json.dumps(formatted_data, indent=2)

    def monitor_and_alert(self, critical_metrics):
        """
        Monitor specific metrics and generate alerts using AI analysis
        """
        for metric in critical_metrics:
            data = self.get_metric_data(metric)
            analysis = self.analyze_metrics(data)
            
            if "critical" in analysis.lower() or "warning" in analysis.lower():
                self.logger.warning(f"Alert for {metric}:\n{analysis}")
            else:
                self.logger.info(f"Status normal for {metric}:\n{analysis}")

    def get_optimization_recommendations(self):
        """
        Generate optimization recommendations based on current metrics
        """
        # Collect relevant metrics for optimization analysis
        metrics_to_analyze = [
            "compute.googleapis.com/instance/cpu/utilization",
            "compute.googleapis.com/instance/memory/utilization",
            "loadbalancing.googleapis.com/https/request_count"
        ]
        
        all_metrics_data = []
        for metric in metrics_to_analyze:
            data = self.get_metric_data(metric)
            all_metrics_data.extend(data)
        
        prompt = """
        As an SRE expert, analyze the current metrics and provide:
        1. Resource optimization recommendations
        2. Cost-saving opportunities
        3. Performance improvement suggestions
        4. Scaling recommendations
        
        Consider best practices for cloud infrastructure management.
        """
        
        recommendations = self.model.predict(
            prompt + "\n" + self._format_metrics_for_analysis(all_metrics_data)
        )
        return recommendations.text

def main():
    # Example usage
    project_id = "your-project-id"
    sre_agent = GCPSREAgent(project_id)
    
    # Define critical metrics to monitor
    critical_metrics = [
        "compute.googleapis.com/instance/cpu/utilization",
        "compute.googleapis.com/instance/memory/utilization",
        "compute.googleapis.com/instance/disk/read_bytes_count",
        "loadbalancing.googleapis.com/https/request_count"
    ]
    
    # Monitor metrics and get recommendations
    sre_agent.monitor_and_alert(critical_metrics)
    recommendations = sre_agent.get_optimization_recommendations()
    print("Optimization Recommendations:")
    print(recommendations)

if __name__ == "__main__":
    main()
