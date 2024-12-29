import pandas as pd
import numpy as np
from dowhy import CausalModel
import dowhy.datasets
from google.cloud import monitoring_v3
from datetime import datetime, timedelta

class GCPMetricsAnalyzer:
    def __init__(self, project_id):
        """
        Initialize the GCP Metrics Analyzer
        """
        self.project_id = project_id
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"
        
    def list_metric_descriptors(self, filter_str=None):
        """
        List available metric descriptors in the project
        
        Args:
            filter_str (str, optional): Filter string to narrow down metrics
            
        Returns:
            list: Available metric descriptors
        """
        try:
            request = monitoring_v3.ListMetricDescriptorsRequest(
                name=self.project_name,
                filter=filter_str
            )
            page_result = self.client.list_metric_descriptors(request=request)
            
            metrics = []
            for descriptor in page_result:
                metrics.append({
                    'type': descriptor.type,
                    'display_name': descriptor.display_name,
                    'description': descriptor.description
                })
            return metrics
        except Exception as e:
            print(f"Error listing metrics: {str(e)}")
            raise
        """
        Initialize the GCP Metrics Analyzer
        
        Args:
            project_id (str): GCP Project ID
        """
        self.project_id = project_id
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def fetch_metric_data(self, metric_type, start_time, end_time, filter_str=None):
        """
        Fetch metric data from GCP Monitoring with error handling
        """
        try:
            # First, verify the metric exists
            metric_descriptor_name = f"{self.project_name}/metricDescriptors/{metric_type}"
            try:
                self.client.get_metric_descriptor(name=metric_descriptor_name)
            except Exception as e:
                print(f"Error: Metric {metric_type} not found. Available metrics can be listed using list_metric_descriptors().")
                raise
        """
        Fetch metric data from GCP Monitoring
        
        Args:
            metric_type (str): Full metric type (e.g., 'compute.googleapis.com/instance/cpu/utilization')
            start_time (datetime): Start time for data collection
            end_time (datetime): End time for data collection
            filter_str (str, optional): Additional filter string
            
        Returns:
            pandas.DataFrame: DataFrame containing the metric data
        """
        interval = monitoring_v3.TimeInterval({
            'start_time': start_time.isoformat() + 'Z',
            'end_time': end_time.isoformat() + 'Z',
        })

        query = monitoring_v3.QueryTimeSeriesRequest(
            name=self.project_name,
            query=f'metric.type="{metric_type}"' + (f' AND {filter_str}' if filter_str else '')
        )

        results = self.client.query_time_series(request=query)
        
        # Process the results into a DataFrame
        data = []
        for series in results:
            for point in series.points:
                data.append({
                    'timestamp': point.interval.end_time.timestamp(),
                    'value': point.value.double_value,
                    'metric_type': metric_type,
                })
        
        return pd.DataFrame(data)

    def prepare_causal_dataset(self, treatment_metric, outcome_metric, start_time, end_time,
                             additional_covariates=None):
        """
        Prepare dataset for causal analysis
        
        Args:
            treatment_metric (str): Metric type for treatment variable
            outcome_metric (str): Metric type for outcome variable
            start_time (datetime): Start time for data collection
            end_time (datetime): End time for data collection
            additional_covariates (list): List of additional metric types to include as covariates
            
        Returns:
            pandas.DataFrame: Prepared dataset for causal analysis
        """
        # Fetch treatment and outcome data
        treatment_data = self.fetch_metric_data(treatment_metric, start_time, end_time)
        outcome_data = self.fetch_metric_data(outcome_metric, start_time, end_time)
        
        # Merge datasets
        dataset = pd.merge(treatment_data, outcome_data, 
                          on='timestamp', 
                          suffixes=('_treatment', '_outcome'))
        
        # Add covariates if specified
        if additional_covariates:
            for covariate in additional_covariates:
                covariate_data = self.fetch_metric_data(covariate, start_time, end_time)
                dataset = pd.merge(dataset, covariate_data,
                                 on='timestamp',
                                 suffixes=('', f'_{covariate.split("/")[-1]}'))
        
        return dataset

    def run_causal_analysis(self, dataset, treatment_col, outcome_col, covariates=None):
        """
        Perform causal analysis using DoWhy
        
        Args:
            dataset (pandas.DataFrame): Prepared dataset
            treatment_col (str): Column name for treatment variable
            outcome_col (str): Column name for outcome variable
            covariates (list): List of covariate column names
            
        Returns:
            dict: Results of causal analysis
        """
        # Define causal graph
        graph = """
        digraph {
            treatment [label="%s"];
            outcome [label="%s"];
        """ % (treatment_col, outcome_col)
        
        if covariates:
            for covariate in covariates:
                graph += f'    {covariate} -> treatment;\n'
                graph += f'    {covariate} -> outcome;\n'
        
        graph += "    treatment -> outcome;\n}"
        
        # Create and fit causal model
        model = CausalModel(
            data=dataset,
            treatment=treatment_col,
            outcome=outcome_col,
            graph=graph
        )
        
        # Identify causal effect
        identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
        
        # Estimate causal effect
        estimate = model.estimate_effect(identified_estimand,
                                       method_name="backdoor.linear_regression")
        
        # Refute results
        refutation_results = model.refute_estimate(identified_estimand, estimate,
                                                 method_name="random_common_cause")
        
        return {
            'estimate': estimate,
            'refutation': refutation_results
        }

def main():
    # Example usage
    analyzer = GCPMetricsAnalyzer('your-project-id')
    
    # Define time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    # Define metrics
    # Use correct GCP metric types
    treatment_metric = 'compute.googleapis.com/instance/cpu/utilization'
    outcome_metric = 'compute.googleapis.com/instance/memory/usage'  # Corrected metric name
    covariates = [
        'compute.googleapis.com/instance/network/received_bytes_count',
        'compute.googleapis.com/instance/disk/read_bytes_count'
    ]
    
    # Prepare dataset
    dataset = analyzer.prepare_causal_dataset(
        treatment_metric=treatment_metric,
        outcome_metric=outcome_metric,
        start_time=start_time,
        end_time=end_time,
        additional_covariates=covariates
    )
    
    # Run analysis
    results = analyzer.run_causal_analysis(
        dataset=dataset,
        treatment_col='value_treatment',
        outcome_col='value_outcome',
        covariates=[col for col in dataset.columns if col.startswith('value_') 
                   and col not in ['value_treatment', 'value_outcome']]
    )
    
    # Print results
    print("Causal Effect Estimate:")
    print(results['estimate'])
    print("\nRefutation Results:")
    print(results['refutation'])

if __name__ == "__main__":
    main()

Version 4 of 4
