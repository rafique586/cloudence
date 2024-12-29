import pandas as pd
import numpy as np
from dowhy import CausalModel
from google.cloud import monitoring_v3
import datetime
from typing import List, Dict, Any

class GCPMetricsAnalyzer:
    def __init__(self, project_id: str):
        """
        Initialize the GCP Metrics Analyzer.
        
        Args:
            project_id (str): GCP project ID
        """
        self.project_id = project_id
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def fetch_metric_data(
        self,
        metric_type: str,
        hours: int = 24,
        filter_str: str = None
    ) -> pd.DataFrame:
        """
        Fetch metric data from GCP Monitoring.
        
        Args:
            metric_type (str): Full metric type (e.g., 'compute.googleapis.com/instance/cpu/utilization')
            hours (int): Hours of data to fetch
            filter_str (str): Additional filter string
            
        Returns:
            pd.DataFrame: DataFrame containing metric data
        """
        now = datetime.datetime.utcnow()
        seconds = hours * 3600
        interval = monitoring_v3.TimeInterval({
            'end_time': now,
            'start_time': now - datetime.timedelta(seconds=seconds)
        })

        results = self.client.list_time_series(
            request={
                "name": self.project_name,
                "filter": f'metric.type = "{metric_type}"' + (f' AND {filter_str}' if filter_str else ''),
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            }
        )

        # Convert to DataFrame
        data = []
        for time_series in results:
            for point in time_series.points:
                data.append({
                    'timestamp': point.interval.end_time,
                    'value': point.value.double_value,
                    'resource': time_series.resource.labels
                })

        return pd.DataFrame(data)

    def perform_causal_analysis(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        common_causes: List[str],
        effect_modifiers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Perform causal analysis using DoWhy.
        
        Args:
            df (pd.DataFrame): Input DataFrame
            treatment_col (str): Column name for treatment variable
            outcome_col (str): Column name for outcome variable
            common_causes (List[str]): List of common causes
            effect_modifiers (List[str]): List of effect modifiers
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Create causal model
        model = CausalModel(
            data=df,
            treatment=treatment_col,
            outcome=outcome_col,
            common_causes=common_causes,
            effect_modifiers=effect_modifiers or []
        )

        # Identify causal effect
        identified_estimand = model.identify_effect()

        # Estimate causal effect
        estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.linear_regression"
        )

        # Refute results
        refutation_results = model.refute_estimate(
            identified_estimand,
            estimate,
            method_name="random_common_cause"
        )

        return {
            'causal_estimate': estimate.value,
            'confidence_intervals': estimate.get_confidence_intervals(),
            'refutation_results': refutation_results
        }

    def analyze_service_metrics(
        self,
        service_metrics: List[str],
        target_metric: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze the causal relationship between service metrics.
        
        Args:
            service_metrics (List[str]): List of metric types to analyze
            target_metric (str): Target metric for causal analysis
            hours (int): Hours of historical data to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Fetch data for all metrics
        metrics_data = {}
        for metric in service_metrics + [target_metric]:
            metrics_data[metric] = self.fetch_metric_data(metric, hours)

        # Combine all metrics into a single DataFrame
        combined_df = pd.DataFrame()
        for metric_name, metric_df in metrics_data.items():
            metric_df = metric_df.resample('5T', on='timestamp').mean()
            combined_df[metric_name] = metric_df['value']

        # Perform causal analysis for each service metric
        results = {}
        for metric in service_metrics:
            analysis_results = self.perform_causal_analysis(
                df=combined_df,
                treatment_col=metric,
                outcome_col=target_metric,
                common_causes=[m for m in service_metrics if m != metric]
            )
            results[metric] = analysis_results

        return results

def main():
    # Example usage
    project_id = "your-project-id"
    analyzer = GCPMetricsAnalyzer(project_id)

    # Define metrics to analyze
    service_metrics = [
        "compute.googleapis.com/instance/cpu/utilization",
        "compute.googleapis.com/instance/memory/utilization",
        "compute.googleapis.com/instance/network/received_bytes_count"
    ]
    target_metric = "compute.googleapis.com/instance/disk/write_bytes_count"

    # Perform analysis
    results = analyzer.analyze_service_metrics(
        service_metrics=service_metrics,
        target_metric=target_metric,
        hours=24
    )

    # Print results
    for metric, analysis in results.items():
        print(f"\nResults for {metric}:")
        print(f"Causal estimate: {analysis['causal_estimate']}")
        print(f"Confidence intervals: {analysis['confidence_intervals']}")
        print(f"Refutation results: {analysis['refutation_results']}")

if __name__ == "__main__":
    main()
Last edited 3 minutes ago


