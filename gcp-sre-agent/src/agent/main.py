# main.py
from google.cloud import aiplatform
from google.cloud import monitoring_v3
from google.cloud import logging_v2
from google.cloud import container_v1
from kubernetes import client, config
import yaml
import datetime
import time
from typing import List, Dict, Any


class GCPSREAgent:
    def __init__(self, project_id: str, config_path: str):
        self.project_id = project_id
        self.config = self.load_config(config_path)
        self.setup_clients()

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def setup_clients(self):
        """Initialize all necessary GCP clients"""
        self.logging_client = logging_v2.Client()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.container_client = container_v1.ClusterManagerClient()

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id)

    async def process_natural_language_query(self, query: str) -> str:
        """Process natural language queries using Vertex AI"""
        endpoint = aiplatform.Endpoint(
            self.config['vertex_ai']['endpoint_name'])
        response = await endpoint.predict([query])
        return response

    def check_kubernetes_clusters(self) -> Dict[str, Any]:
        """Monitor Kubernetes clusters across regions"""
        cluster_status = {}

        for region in self.config['kubernetes']['regions']:
            try:
                request = container_v1.ListClustersRequest(
                    parent=f"projects/{self.project_id}/locations/{region}"
                )
                response = self.container_client.list_clusters(request=request)

                for cluster in response.clusters:
                    cluster_status[f"{
                        region}/{cluster.name}"] = self.check_cluster_pods(cluster)
            except Exception as e:
                cluster_status[region] = f"Error: {str(e)}"

        return cluster_status

    def check_cluster_pods(self, cluster) -> Dict[str, Any]:
        """Check pods status in all namespaces of a cluster"""
        config.load_kube_config()
        v1 = client.CoreV1Api()

        pod_status = {}
        try:
            pods = v1.list_pod_for_all_namespaces(watch=False)
            for pod in pods.items:
                namespace = pod.metadata.namespace
                if namespace not in pod_status:
                    pod_status[namespace] = {'healthy': 0, 'unhealthy': 0}

                if pod.status.phase == 'Running':
                    pod_status[namespace]['healthy'] += 1
                else:
                    pod_status[namespace]['unhealthy'] += 1
        except Exception as e:
            pod_status['error'] = str(e)

        return pod_status

    def monitor_error_logs(self) -> Dict[str, List[Dict]]:
        """Monitor logs for error codes specified in config"""
        error_logs = {}

        for error_code in self.config['logging']['error_codes']:
            filter_str = (
                f'resource.type="k8s_container" '
                f'severity>=ERROR '
                f'httpRequest.status={error_code}'
            )

            try:
                entries = self.logging_client.list_entries(
                    filter_=filter_str,
                    order_by="timestamp desc",
                    page_size=self.config['logging']['max_entries']
                )

                error_logs[error_code] = [
                    {
                        'timestamp': entry.timestamp,
                        'resource': entry.resource.type,
                        'message': entry.payload
                    }
                    for entry in entries
                ]
            except Exception as e:
                error_logs[error_code] = [{'error': str(e)}]

        return error_logs

    def monitor_dashboards(self) -> Dict[str, Any]:
        """Monitor dashboards specified in config"""
        dashboard_metrics = {}

        for dashboard in self.config['monitoring']['dashboards']:
            try:
                now = time.time()
                interval = monitoring_v3.TimeInterval({
                    'end_time': {'seconds': int(now)},
                    'start_time': {'seconds': int(now - self.config['monitoring']['interval_seconds'])}
                })

                dashboard_metrics[dashboard['name']] = self.get_dashboard_metrics(
                    dashboard['metric_types'],
                    interval
                )
            except Exception as e:
                dashboard_metrics[dashboard['name']] = f"Error: {str(e)}"

        return dashboard_metrics

    def get_dashboard_metrics(self, metric_types: List[str], interval) -> Dict[str, Any]:
        """Get metrics for specific dashboard"""
        metrics_data = {}

        for metric_type in metric_types:
            try:
                request = monitoring_v3.ListTimeSeriesRequest(
                    name=f"projects/{self.project_id}",
                    filter=f'metric.type = "{metric_type}"',
                    interval=interval,
                    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                )
                results = self.monitoring_client.list_time_series(
                    request=request)
                metrics_data[metric_type] = [
                    point for series in results for point in series.points]
            except Exception as e:
                metrics_data[metric_type] = f"Error: {str(e)}"

        return metrics_data

    async def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        results = {
            'timestamp': datetime.datetime.now().isoformat(),
            'kubernetes_status': self.check_kubernetes_clusters(),
            'error_logs': self.monitor_error_logs(),
            'dashboard_metrics': self.monitor_dashboards()
        }

        return results
