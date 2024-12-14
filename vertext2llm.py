from google.cloud import monitoring_v3
from google.cloud import aiplatform
from vertexai.language_models import TextGenerationModel
from datetime import datetime, timedelta
import pandas as pd
import json

def get_k8s_metrics(project_id, cluster_name, interval_minutes=60):
    """
    Query multiple Kubernetes metrics from Cloud Monitoring with proper pagination
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"
    
    now = datetime.utcnow()
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(now.timestamp())},
            "start_time": {"seconds": int((now - timedelta(minutes=interval_minutes)).timestamp())},
        }
    )

    # Define metrics to collect
    metric_types = [
        "kubernetes.io/container/cpu/core_usage_time",
        "kubernetes.io/container/memory/used_bytes",
        "kubernetes.io/container/network/received_bytes_count",
        "kubernetes.io/container/network/sent_bytes_count",
        "kubernetes.io/pod/volume/used_bytes"
    ]

    all_metrics = {}
    
    for metric_type in metric_types:
        metric_name = metric_type.split('/')[-1]
        all_metrics[metric_name] = []
        
        try:
            request = monitoring_v3.ListTimeSeriesRequest(
                name=project_name,
                filter=f'resource.type="k8s_container" AND resource.labels.cluster_name="{cluster_name}"'
                       f' AND metric.type="{metric_type}"',
                interval=interval,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            )
            
            # Handle pagination
            while True:
                try:
                    page_result = client.list_time_series(request=request)
                    
                    for time_series in page_result:
                        # Extract labels once per time series
                        resource_labels = {
                            'container': time_series.resource.labels['container_name'],
                            'namespace': time_series.resource.labels['namespace_name'],
                            'pod': time_series.resource.labels['pod_name']
                        }
                        
                        # Process all points for this time series
                        metrics = [
                            {
                                'timestamp': point.interval.end_time.timestamp(),
                                'value': point.value.double_value if hasattr(point.value, 'double_value') 
                                        else point.value.int64_value,
                                **resource_labels
                            }
                            for point in time_series.points
                        ]
                        
                        all_metrics[metric_name].extend(metrics)
                    
                    # Check if there are more pages
                    next_page_token = page_result.next_page_token
                    if not next_page_token:
                        break
                        
                    # Update the request with the next page token
                    request.page_token = next_page_token
                    
                except Exception as e:
                    print(f"Error processing page for {metric_type}: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"Error collecting {metric_type}: {str(e)}")
            continue
        
        # Log the number of data points collected
        print(f"Collected {len(all_metrics[metric_name])} data points for {metric_name}")
    
    return all_metrics

def prepare_metrics_summary(metrics_data):
    """
    Prepare a summary of the metrics for LLM analysis
    """
    summary = {}
    
    for metric_name, data in metrics_data.items():
        if not data:
            continue
            
        df = pd.DataFrame(data)
        
        # Calculate statistics per container
        container_stats = df.groupby('container').agg({
            'value': ['mean', 'max', 'min', 'std']
        }).round(2)
        
        summary[metric_name] = {
            'overall_stats': {
                'mean': float(df['value'].mean()),
                'max': float(df['value'].max()),
                'min': float(df['value'].min()),
                'std': float(df['value'].std())
            },
            'container_stats': container_stats.to_dict()
        }
    
    return summary

def generate_llm_analysis(project_id, metrics_summary, location="us-central1"):
    """
    Use Vertex AI's LLM to analyze the metrics
    """
    aiplatform.init(project=project_id, location=location)
    
    # Initialize the model
    model = TextGenerationModel.from_pretrained("text-bison@002")
    
    # Prepare the prompt
    prompt = f"""
    Analyze the following Kubernetes cluster metrics and provide insights:
    
    Metrics Summary:
    {json.dumps(metrics_summary, indent=2)}
    
    Please provide:
    1. Key observations about resource usage patterns
    2. Potential optimization recommendations
    3. Any anomalies or concerns
    4. Capacity planning suggestions
    
    Focus on practical insights that would be valuable for cluster administrators.
    """
    
    # Generate analysis
    response = model.predict(
        prompt,
        temperature=0.2,
        max_output_tokens=1024,
        top_k=40,
        top_p=0.8,
    )
    
    return response.text

def main():
    # Configuration
    project_id = "your-project-id"
    cluster_name = "your-cluster-name"
    
    # Collect metrics
    print("Collecting Kubernetes metrics...")
    metrics_data = get_k8s_metrics(
        project_id=project_id,
        cluster_name=cluster_name
    )
    
    # Prepare metrics summary
    print("Preparing metrics summary...")
    metrics_summary = prepare_metrics_summary(metrics_data)
    
    # Generate LLM analysis
    print("Generating analysis using Vertex AI LLM...")
    analysis = generate_llm_analysis(project_id, metrics_summary)
    
    # Print results
    print("\nAnalysis Results:")
    print("----------------")
    print(analysis)
    
    # Optionally save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"k8s_analysis_{timestamp}.txt", "w") as f:
        f.write(analysis)

if __name__ == "__main__":
    main()
