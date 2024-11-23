from google.cloud import container_v1, monitoring_v1, logging_v2, error_reporting_v2
from google.cloud.monitoring_v3 import query
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any, Optional, Callable
import json
import aiohttp
import pandas as pd
import numpy as np
from dataclasses import dataclass
import yaml
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

@dataclass
class AlertConfig:
    """Alert configuration settings"""
    threshold: float
    comparison: str  # 'gt', 'lt', 'eq'
    window_minutes: int
    callback: Callable
    description: str

class AlertManager:
    """Manages alerting for metrics"""
    def __init__(self):
        self.alerts: Dict[str, AlertConfig] = {}
        self.alert_history: List[Dict] = []
        
    def add_alert(self, metric_name: str, config: AlertConfig):
        self.alerts[metric_name] = config
        
    async def check_alert(self, metric_name: str, value: float) -> Optional[Dict]:
        if metric_name not in self.alerts:
            return None
            
        config = self.alerts[metric_name]
        should_alert = False
        
        if config.comparison == 'gt' and value > config.threshold:
            should_alert = True
        elif config.comparison == 'lt' and value < config.threshold:
            should_alert = True
        elif config.comparison == 'eq' and value == config.threshold:
            should_alert = True
            
        if should_alert:
            alert_info = {
                'metric': metric_name,
                'value': value,
                'threshold': config.threshold,
                'timestamp': datetime.utcnow().isoformat(),
                'description': config.description
            }
            self.alert_history.append(alert_info)
            await config.callback(alert_info)
            return alert_info
        return None

class MetricRegistry:
    """Registry for monitoring metrics"""
    def __init__(self):
        self.metrics: Dict[str, GCPMonitoringMetric] = {}
        self.prom_registry = CollectorRegistry()
        
    def register(self, name: str, metric: 'GCPMonitoringMetric'):
        self.metrics[name] = metric
        # Create Prometheus gauge for the metric
        metric.prom_gauge = Gauge(
            f"k8s_{name}_metric",
            f"Kubernetes {name} metric",
            ['pod', 'container'],
            registry=self.prom_registry
        )

class BaseMetric(GCPMonitoringMetric):
    """Enhanced base metric class"""
    def __init__(self, project_id: str, location: str, cluster_name: str):
        super().__init__(project_id, location, cluster_name)
        self.historical_data: List[Dict] = []
        self.prom_gauge = None
        
    def store_historical_data(self, data: Dict):
        self.historical_data.append({
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        })
        if len(self.historical_data) > 1000:  # Keep last 1000 data points
            self.historical_data.pop(0)
            
    def update_prometheus_metrics(self, data: Dict):
        if self.prom_gauge:
            for key, value in data.items():
                pod, container = key.split('/')
                self.prom_gauge.labels(pod=pod, container=container).set(value['value'])

class DiskUsageMetric(BaseMetric):
    """Disk usage monitoring"""
    def get_metric_query(self) -> str:
        return """
        fetch k8s_container
        | metric 'kubernetes.io/container/disk/used_bytes'
        | align mean(1m)
        | every 1m
        """
        
    def process_response(self, response: Any) -> Dict:
        results = {}
        for time_series in response:
            pod_name = time_series.resource.labels.get('pod_name', 'unknown')
            container_name = time_series.resource.labels.get('container_name', 'unknown')
            if time_series.points:
                results[f"{pod_name}/{container_name}"] = {
                    'value': time_series.points[0].value.double_value / (1024 * 1024 * 1024),  # Convert to GB
                    'timestamp': time_series.points[0].interval.end_time.isoformat()
                }
        return results

class PodHealthMetric(BaseMetric):
    """Pod health monitoring"""
    def get_metric_query(self) -> str:
        return """
        fetch k8s_pod
        | metric 'kubernetes.io/pod/status/phase'
        | align mean(1m)
        | every 1m
        """
        
    def process_response(self, response: Any) -> Dict:
        results = {}
        for time_series in response:
            pod_name = time_series.resource.labels.get('pod_name', 'unknown')
            if time_series.points:
                results[f"{pod_name}/status"] = {
                    'value': time_series.points[0].value.int64_value,
                    'timestamp': time_series.points[0].interval.end_time.isoformat()
                }
        return results

class LogAnalyzer:
    """Advanced log analysis"""
    def __init__(self):
        self.error_patterns = {
            'oom_kill': r'Out of Memory|OOMKilled',
            'crash_loop': r'CrashLoopBackOff',
            'pull_error': r'ImagePullBackOff|ErrImagePull'
        }
        
    def analyze_logs(self, logs: List[Dict]) -> Dict:
        analysis = {
            'error_counts': {},
            'severity_distribution': {},
            'timeline': [],
            'potential_issues': []
        }
        
        df = pd.DataFrame(logs)
        
        # Analyze error patterns
        for pattern_name, pattern in self.error_patterns.items():
            mask = df['message'].str.contains(pattern, na=False, regex=True)
            analysis['error_counts'][pattern_name] = mask.sum()
            
        # Severity distribution
        analysis['severity_distribution'] = df['severity'].value_counts().to_dict()
        
        # Timeline analysis
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        timeline = df.set_index('timestamp').resample('5T').size()
        analysis['timeline'] = [
            {'timestamp': str(ts), 'count': count}
            for ts, count in timeline.items()
        ]
        
        # Identify potential issues
        if analysis['error_counts'].get('oom_kill', 0) > 0:
            analysis['potential_issues'].append({
                'type': 'Memory Pressure',
                'description': 'Containers are being killed due to memory constraints'
            })
            
        return analysis

class EnhancedKubernetesMonitoringAgent:
    """Enhanced AI agent for Kubernetes monitoring"""
    def __init__(self, project_id: str, location: str, cluster_name: str):
        self.project_id = project_id
        self.location = location
        self.cluster_name = cluster_name
        
        # Initialize clients
        self.container_client = container_v1.ClusterManagerClient()
        self.logging_client = logging_v2.Client()
        self.error_client = error_reporting_v2.ReportErrorsServiceClient()
        
        # Initialize components
        self.metric_registry = MetricRegistry()
        self.alert_manager = AlertManager()
        self.log_analyzer = LogAnalyzer()
        
        # Register default metrics
        self._register_default_metrics()
        
    def _register_default_metrics(self):
        """Register default monitoring metrics"""
        metrics = {
            'cpu': CPUUtilizationMetric(self.project_id, self.location, self.cluster_name),
            'memory': MemoryUsageMetric(self.project_id, self.location, self.cluster_name),
            'disk': DiskUsageMetric(self.project_id, self.location, self.cluster_name),
            'network': NetworkUsageMetric(self.project_id, self.location, self.cluster_name),
            'pod_health': PodHealthMetric(self.project_id, self.location, self.cluster_name)
        }
        
        for name, metric in metrics.items():
            self.metric_registry.register(name, metric)
            
    async def setup_default_alerts(self, webhook_url: Optional[str] = None):
        """Setup default alerting thresholds"""
        async def alert_callback(alert_info: Dict):
            if webhook_url:
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=alert_info)
            print(f"ALERT: {alert_info}")
            
        self.alert_manager.add_alert('cpu', AlertConfig(
            threshold=80.0,
            comparison='gt',
            window_minutes=5,
            callback=alert_callback,
            description='CPU utilization above 80%'
        ))
        
        self.alert_manager.add_alert('memory', AlertConfig(
            threshold=90.0,
            comparison='gt',
            window_minutes=5,
            callback=alert_callback,
            description='Memory utilization above 90%'
        ))

    async def monitor(self) -> Dict:
        """Enhanced monitoring method"""
        # Collect metrics
        metric_tasks = [
            self.get_metric_data(metric_name)
            for metric_name in self.metric_registry.metrics
        ]
        
        # Collect logs and cluster info
        tasks = [
            self.get_cluster_info(),
            self.get_logs(),
            *metric_tasks
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Process results
        cluster_info = results[0]
        logs = results[1]
        metrics_data = {
            metric_name: results[i+2]
            for i, metric_name in enumerate(self.metric_registry.metrics)
        }
        
        # Analyze logs
        log_analysis = self.log_analyzer.analyze_logs(logs)
        
        # Check alerts
        alerts = []
        for metric_name, metric_data in metrics_data.items():
            for pod_data in metric_data.values():
                alert = await self.alert_manager.check_alert(
                    metric_name, pod_data['value']
                )
                if alert:
                    alerts.append(alert)
        
        # Update Prometheus metrics
        for metric_name, metric_data in metrics_data.items():
            metric = self.metric_registry.metrics[metric_name]
            metric.update_prometheus_metrics(metric_data)
            
        # Push to Prometheus Pushgateway
        try:
            push_to_gateway(
                'localhost:9091',
                job='kubernetes_metrics',
                registry=self.metric_registry.prom_registry
            )
        except Exception as e:
            print(f"Error pushing to Prometheus: {e}")
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'cluster_info': cluster_info,
            'metrics': metrics_data,
            'logs': {
                'raw': logs[:100],  # Last 100 logs
                'analysis': log_analysis
            },
            'alerts': alerts
        }

    def export_config(self, filename: str):
        """Export monitoring configuration"""
        config = {
            'cluster': {
                'project_id': self.project_id,
                'location': self.location,
                'cluster_name': self.cluster_name
            },
            'metrics': list(self.metric_registry.metrics.keys()),
            'alerts': {
                name: {
                    'threshold': alert.threshold,
                    'comparison': alert.comparison,
                    'window_minutes': alert.window_minutes,
                    'description': alert.description
                }
                for name, alert in self.alert_manager.alerts.items()
            }
        }
        
        with open(filename, 'w') as f:
            yaml.dump(config, f)

async def main():
    # Configuration
    project_id = "your-project-id"
    location = "your-cluster-location"
    cluster_name = "your-cluster-name"
    webhook_url = "your-webhook-url"  # Optional
    
    # Initialize agent
    agent = EnhancedKubernetesMonitoringAgent(project_id, location, cluster_name)
    
    # Setup alerts
    await agent.setup_default_alerts(webhook_url)
    
    # Export configuration
    agent.export_config('monitoring_config.yaml')
    
    # Run monitoring
    while True:
        try:
            monitoring_data = await agent.monitor()
            print(json.dumps(monitoring_data, indent=2))
            
            # Wait for next iteration
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
