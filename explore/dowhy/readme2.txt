important changes to fix the error:

Corrected the metric name from compute.googleapis.com/instance/memory/utilization to compute.googleapis.com/instance/memory/usage
Added a new list_metric_descriptors() method to help you find available metrics
Added error handling and validation for metric types

To use the updated code, you can first list available metrics:
pythonCopyanalyzer = GCPMetricsAnalyzer('your-project-id')

# List compute engine metrics
compute_metrics = analyzer.list_metric_descriptors(
    filter_str='metric.type = starts_with("compute.googleapis.com")'
)

# Print available metrics
for metric in compute_metrics:
    print(f"Type: {metric['type']}")
    print(f"Display name: {metric['display_name']}")
    print(f"Description: {metric['description']}\n")
Common GCP Compute Engine metrics you might want to use:
pythonCopy# CPU utilization
'compute.googleapis.com/instance/cpu/utilization'

# Memory usage
'compute.googleapis.com/instance/memory/usage'

# Disk read bytes
'compute.googleapis.com/instance/disk/read_bytes_count'

# Network received bytes
'compute.googleapis.com/instance/network/received_bytes_count'
