import os
from kubernetes import client, config, watch
from google.cloud import aiplatform
import vertexai
from vertexai.language_models import TextGenerationModel
import json
import logging
from typing import Dict, List, Any, Optional
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from prometheus_api_client import PrometheusConnect

class KubernetesAIAgent:
    """
    An AI-powered Kubernetes management and monitoring agent.
    
    This agent combines natural language processing capabilities with Kubernetes API
    interactions to provide intelligent cluster management, monitoring, and analysis.
    It uses Google's Gemini model for NLP and can integrate with Prometheus for
    advanced metrics collection.
    
    Key Features:
    - Natural language interaction with Kubernetes cluster
    - Advanced monitoring and metrics analysis
    - Automated troubleshooting and diagnostics
    - Cost optimization analysis
    - Resource usage tracking and optimization
    """

    def __init__(self, context: str = None, prometheus_url: str = None):
        """
        Initialize the Kubernetes AI Agent with necessary clients and configurations.
        
        Args:
            context (str, optional): Kubernetes context to use
            prometheus_url (str, optional): URL for Prometheus metrics server
            
        The initialization process:
        1. Sets up Kubernetes configuration
        2. Initializes various Kubernetes API clients
        3. Sets up Prometheus connection if URL provided
        4. Initializes Vertex AI for natural language processing
        5. Configures logging and caching
        """
        # Initialize Kubernetes configuration - either use provided context or default
        if context:
            config.load_kube_config(context=context)
        else:
            config.load_kube_config()
            
        # Initialize various Kubernetes API clients for different resource types
        self.core_v1 = client.CoreV1Api()  # For core resources (pods, services, etc.)
        self.apps_v1 = client.AppsV1Api()  # For application resources (deployments, statefulsets)
        self.batch_v1 = client.BatchV1Api()  # For batch workloads (jobs)
        self.autoscaling_v1 = client.AutoscalingV1Api()  # For HPA and scaling
        self.custom_objects = client.CustomObjectsApi()  # For CRDs and custom resources
        
        # Initialize Prometheus client if URL is provided
        # This enables advanced metrics collection and analysis
        self.prom = PrometheusConnect(url=prometheus_url) if prometheus_url else None
        
        # Initialize Vertex AI with Gemini model for natural language processing
        vertexai.init(project="your-project-id", location="us-central1")
        self.model = TextGenerationModel.from_pretrained("gemini-pro")
        
        # Setup logging with detailed format
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache for performance optimization
        # Cache stores frequently accessed data to reduce API calls
        self.cache = {}
        self.cache_timeout = 300  # Cache timeout in seconds (5 minutes)

    def process_natural_language_query(self, query: str) -> str:
        """
        Process natural language queries and convert them to Kubernetes operations.
        
        Args:
            query (str): Natural language query from user
            
        Returns:
            str: AI-generated response based on query analysis and execution
            
        This method:
        1. Analyzes the input query using Gemini
        2. Determines the intent and required operations
        3. Executes appropriate Kubernetes operations
        4. Returns natural language response
        """
        intent_prompt = """
        Analyze the following Kubernetes-related query and determine:
        1. Primary intent (list, describe, monitor, troubleshoot, modify)
        2. Resource type (pods, nodes, services, deployments, etc.)
        3. Scope (specific namespace, all namespaces, specific resource name)
        4. Time range (if applicable)
        5. Additional filters or conditions
        
        Query: {query}
        
        Provide a structured analysis that can be mapped to Kubernetes API calls.
        """
        
        # Get AI analysis of the query intent
        intent_analysis = self.model.predict(intent_prompt.format(query=query))
        
        # Execute the interpreted query based on AI analysis
        return self._execute_complex_query(intent_analysis.text, query)

    def _execute_complex_query(self, analysis: str, original_query: str) -> str:
        """
        Execute complex Kubernetes operations based on AI analysis.
        
        Args:
            analysis (str): AI-generated analysis of the query
            original_query (str): Original user query
            
        Returns:
            str: Result of the executed operation with AI-generated explanation
            
        This method maps the analyzed intent to specific Kubernetes operations
        and handles various types of queries including metrics, events, resources,
        troubleshooting, and cost optimization.
        """
        query_lower = original_query.lower()
        
        # Route the query to appropriate handler based on keywords
        if "metrics" in query_lower or "performance" in query_lower:
            return self.get_performance_metrics()
        elif "events" in query_lower or "logs" in query_lower:
            return self.get_cluster_events()
        elif "capacity" in query_lower or "resource" in query_lower:
            return self.analyze_resource_usage()
        elif "troubleshoot" in query_lower or "debug" in query_lower:
            return self.troubleshoot_cluster_issues()
        elif "cost" in query_lower or "optimization" in query_lower:
            return self.analyze_cost_optimization()
        
        # Default to basic query handling if no specific handler matches
        return super()._execute_interpreted_query(analysis, original_query)

    def get_performance_metrics(self) -> str:
        """
        Collect and analyze comprehensive performance metrics from the cluster.
        
        Returns:
            str: AI-generated analysis of cluster performance metrics
            
        This method:
        1. Collects various types of metrics (node, pod, network, resource)
        2. Analyzes the metrics using AI
        3. Provides insights and recommendations
        """
        # Collect different types of metrics
        metrics = {
            "node_metrics": self._get_node_metrics(),
            "pod_metrics": self._get_pod_metrics(),
            "network_metrics": self._get_network_metrics(),
            "resource_usage": self._get_resource_usage_metrics()
        }
        
        # Define prompt for AI analysis
        analysis_prompt = """
        Analyze these Kubernetes performance metrics and provide insights:
        {metrics}
        
        Focus on:
        1. Resource utilization patterns
        2. Performance bottlenecks
        3. Optimization opportunities
        4. Capacity planning recommendations
        """
        
        # Get AI analysis of metrics
        analysis = self.model.predict(analysis_prompt.format(metrics=json.dumps(metrics, indent=2)))
        return analysis.text

    def _get_node_metrics(self) -> Dict:
        """
        Collect detailed metrics for all nodes in the cluster.
        
        Returns:
            Dict: Collection of node-level metrics
            
        This method uses Prometheus queries to collect:
        - CPU usage
        - Memory usage
        - Disk usage
        - Network traffic
        """
        metrics = {}
        if self.prom:
            # Define Prometheus queries for different metrics
            queries = {
                "cpu_usage": 'sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (instance)',
                "memory_usage": 'node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes',
                "disk_usage": 'node_filesystem_size_bytes - node_filesystem_free_bytes',
                "network_traffic": 'sum(rate(node_network_receive_bytes_total[5m])) by (instance)'
            }
            
            # Execute each query and store results
            for metric_name, query in queries.items():
                metrics[metric_name] = self.prom.custom_query(query)
                
        return metrics

    def analyze_resource_usage(self) -> str:
        """
        Perform comprehensive analysis of cluster resource usage.
        
        Returns:
            str: AI-generated analysis of resource usage patterns
            
        This method analyzes:
        1. Compute resource utilization
        2. Memory usage patterns
        3. Storage utilization
        4. Network resource consumption
        """
        # Collect resource usage data
        usage_data = {
            "compute_resources": self._analyze_compute_resources(),
            "memory_resources": self._analyze_memory_resources(),
            "storage_resources": self._analyze_storage_resources(),
            "network_resources": self._analyze_network_resources()
        }
        
        # Define analysis prompt for AI
        analysis_prompt = """
        Analyze the resource usage patterns and provide:
        1. Current utilization summary
        2. Resource bottlenecks
        3. Scaling recommendations
        4. Optimization opportunities
        
        Resource data:
        {data}
        """
        
        # Get AI analysis
        analysis = self.model.predict(analysis_prompt.format(data=json.dumps(usage_data, indent=2)))
        return analysis.text

    def _analyze_resource_allocation(self) -> Dict:
        """
        Analyze resource allocation patterns across the cluster.
        
        Returns:
            Dict: Analysis of resource allocation patterns
            
        This method examines:
        - CPU requests and limits
        - Memory requests and limits
        - Resource allocation patterns
        - Potential resource conflicts
        """
        pods = self.core_v1.list_pod_for_all_namespaces()
        allocations = {
            "cpu_requests": [],
            "memory_requests": [],
            "cpu_limits": [],
            "memory_limits": []
        }
        
        # Analyze resource specifications for each pod
        for pod in pods.items:
            for container in pod.spec.containers:
                # Check resource requests
                if container.resources.requests:
                    if container.resources.requests.get('cpu'):
                        allocations["cpu_requests"].append({
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "request": container.resources.requests['cpu']
                        })
                    if container.resources.requests.get('memory'):
                        allocations["memory_requests"].append({
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "request": container.resources.requests['memory']
                        })
                
                # Check resource limits
                if container.resources.limits:
                    if container.resources.limits.get('cpu'):
                        allocations["cpu_limits"].append({
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "limit": container.resources.limits['cpu']
                        })
                    if container.resources.limits.get('memory'):
                        allocations["memory_limits"].append({
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "limit": container.resources.limits['memory']
                        })
                        
        return allocations

    def monitor_resource_trends(self, duration_hours: int = 24) -> str:
        """
        Monitor and analyze resource usage trends over time.
        
        Args:
            duration_hours (int): Time period to analyze in hours
            
        Returns:
            str: AI-generated analysis of resource usage trends
            
        This method:
        1. Collects historical metric data
        2. Analyzes trends and patterns
        3. Identifies anomalies
        4. Provides recommendations
        """
        if not self.prom:
            return "Prometheus connection not configured for metric collection"
            
        # Define metric queries for different resources
        metric_queries = {
            "cpu_usage_trend": 'rate(container_cpu_usage_seconds_total[24h])',
            "memory_usage_trend": 'container_memory_usage_bytes',
            "network_io_trend": 'rate(container_network_transmit_bytes_total[24h])',
            "disk_io_trend": 'rate(container_fs_io_time_seconds_total[24h])'
        }
        
        # Collect trend data
        trends = {}
        for metric_name, query in metric_queries.items():
            try:
                result = self.prom.custom_query(query)
                trends[metric_name] = result
            except Exception as e:
                self.logger.error(f"Error collecting {metric_name}: {str(e)}")
                
        # Define analysis prompt
        analysis_prompt = f"""
        Analyze these resource usage trends over the past {duration_hours} hours:
        {json.dumps(trends, indent=2)}
        
        Provide:
        1. Usage patterns and trends
        2. Anomalies or concerning patterns
        3. Capacity planning recommendations
        4. Performance optimization suggestions
        """
        
        # Get AI analysis of trends
        analysis = self.model.predict(analysis_prompt)
        return analysis.text

def main():
    """
    Example usage of the Kubernetes AI Agent with various queries
    """
    # Initialize agent with optional Prometheus integration
    agent = KubernetesAIAgent(
        prometheus_url="http://prometheus-server:9090"  # Optional Prometheus URL
    )
    
    # Example complex queries demonstrating different capabilities
    queries = [
        "Show cluster performance metrics for the last 24 hours",
        "Analyze resource usage and suggest optimizations",
        "Check for any critical issues or warnings in the cluster",
        "Provide cost optimization recommendations",
        "Monitor resource usage trends and identify potential issues"
    ]
    
    # Process each query and display results
    for query in queries:
        print(f"\nQuery: {query}")
        print("Response:")
        response = agent.process_natural_language_query(query)
        print(response)
        print("-" * 80)

if __name__ == "__main__":
    main()
