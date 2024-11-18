"""
Enhanced Kubernetes AI Agent with comprehensive object fetching capabilities
"""

import os
from kubernetes import client, config, watch
from google.cloud import aiplatform
import vertexai
from vertexai.language_models import TextGenerationModel
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

@dataclass
class KubernetesObjectStatus:
    """Data class for Kubernetes object status"""
    name: str
    namespace: str
    status: str
    age: str
    conditions: List[Dict[str, Any]]
    labels: Dict[str, str]
    additional_info: Dict[str, Any]

class KubernetesAIAgent:
    def __init__(self, context: str = None, prometheus_url: str = None):
        """Initialize the enhanced Kubernetes AI Agent"""
        # Initialize Kubernetes configuration
        if context:
            config.load_kube_config(context=context)
        else:
            config.load_kube_config()
            
        # Initialize API clients
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.storage_v1 = client.StorageV1Api()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def get_namespaces(self) -> str:
        """
        Fetch and analyze all Kubernetes namespaces with detailed status
        
        Returns:
            str: AI-generated analysis of namespace status
        """
        try:
            namespaces = self.core_v1.list_namespace()
            namespace_details = []
            
            for ns in namespaces.items:
                # Get resource quotas
                quotas = self.core_v1.list_namespaced_resource_quota(ns.metadata.name)
                # Get limit ranges
                limits = self.core_v1.list_namespaced_limit_range(ns.metadata.name)
                
                namespace_info = {
                    "name": ns.metadata.name,
                    "status": ns.status.phase,
                    "age": self._get_age(ns.metadata.creation_timestamp),
                    "labels": ns.metadata.labels or {},
                    "annotations": ns.metadata.annotations or {},
                    "quotas": [
                        {
                            "name": quota.metadata.name,
                            "specs": quota.spec.hard if quota.spec else {}
                        } for quota in quotas.items
                    ],
                    "limits": [
                        {
                            "name": limit.metadata.name,
                            "limits": [
                                {
                                    "type": item.type,
                                    "max": item.max if hasattr(item, 'max') else {},
                                    "min": item.min if hasattr(item, 'min') else {},
                                } for item in limit.spec.limits
                            ] if limit.spec and limit.spec.limits else []
                        } for limit in limits.items
                    ]
                }
                namespace_details.append(namespace_info)

            # Generate AI analysis
            analysis_prompt = f"""
            Analyze these Kubernetes namespaces and provide insights:
            {json.dumps(namespace_details, indent=2)}
            
            Include:
            1. Total number of namespaces
            2. Status summary
            3. Resource quota utilization
            4. Potential issues or concerns
            5. Best practice recommendations
            """
            
            return await self._get_ai_analysis(analysis_prompt)
            
        except Exception as e:
            self.logger.error(f"Error fetching namespaces: {str(e)}")
            raise

    async def get_services(self, namespace: Optional[str] = None) -> str:
        """
        Fetch and analyze Kubernetes services
        
        Args:
            namespace: Optional namespace to filter services
            
        Returns:
            str: AI-generated analysis of services
        """
        try:
            if namespace:
                services = self.core_v1.list_namespaced_service(namespace)
            else:
                services = self.core_v1.list_service_for_all_namespaces()
                
            service_details = []
            for svc in services.items:
                # Get endpoints for the service
                endpoints = self.core_v1.list_namespaced_endpoints(
                    svc.metadata.namespace,
                    field_selector=f'metadata.name={svc.metadata.name}'
                )
                
                service_info = {
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "external_ips": svc.spec.external_i_ps if hasattr(svc.spec, 'external_i_ps') else [],
                    "ports": [
                        {
                            "port": port.port,
                            "target_port": port.target_port,
                            "protocol": port.protocol,
                            "name": port.name if hasattr(port, 'name') else None
                        } for port in svc.spec.ports
                    ],
                    "selector": svc.spec.selector or {},
                    "endpoints": [
                        {
                            "addresses": [addr.ip for addr in subset.addresses] if subset.addresses else [],
                            "ports": [
                                {
                                    "port": port.port,
                                    "protocol": port.protocol
                                } for port in subset.ports
                            ] if subset.ports else []
                        } for subset in endpoints.items[0].subsets
                    ] if endpoints.items else []
                }
                service_details.append(service_info)

            analysis_prompt = f"""
            Analyze these Kubernetes services and provide insights:
            {json.dumps(service_details, indent=2)}
            
            Include:
            1. Total number of services by type
            2. Service health status
            3. Endpoint availability
            4. Network exposure analysis
            5. Security recommendations
            """
            
            return await self._get_ai_analysis(analysis_prompt)
            
        except Exception as e:
            self.logger.error(f"Error fetching services: {str(e)}")
            raise

    async def get_deployments(self, namespace: Optional[str] = None) -> str:
        """
        Fetch and analyze Kubernetes deployments
        
        Args:
            namespace: Optional namespace to filter deployments
            
        Returns:
            str: AI-generated analysis of deployments
        """
        try:
            if namespace:
                deployments = self.apps_v1.list_namespaced_deployment(namespace)
            else:
                deployments = self.apps_v1.list_deployment_for_all_namespaces()
                
            deployment_details = []
            for deploy in deployments.items:
                # Get associated pods
                pods = self.core_v1.list_namespaced_pod(
                    deploy.metadata.namespace,
                    label_selector=','.join(f'{k}={v}' for k, v in (deploy.spec.selector.match_labels or {}).items())
                )
                
                deployment_info = {
                    "name": deploy.metadata.name,
                    "namespace": deploy.metadata.namespace,
                    "replicas": {
                        "desired": deploy.spec.replicas,
                        "available": deploy.status.available_replicas or 0,
                        "ready": deploy.status.ready_replicas or 0,
                        "unavailable": deploy.status.unavailable_replicas or 0
                    },
                    "strategy": {
                        "type": deploy.spec.strategy.type,
                        "max_surge": deploy.spec.strategy.rolling_update.max_surge if deploy.spec.strategy.rolling_update else None,
                        "max_unavailable": deploy.spec.strategy.rolling_update.max_unavailable if deploy.spec.strategy.rolling_update else None
                    },
                    "conditions": [
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason,
                            "message": condition.message
                        } for condition in (deploy.status.conditions or [])
                    ],
                    "pods": [
                        {
                            "name": pod.metadata.name,
                            "status": pod.status.phase,
                            "ready": all(container.ready for container in (pod.status.container_statuses or [])),
                            "restarts": sum(container.restart_count for container in (pod.status.container_statuses or []))
                        } for pod in pods.items
                    ]
                }
                deployment_details.append(deployment_info)

            analysis_prompt = f"""
            Analyze these Kubernetes deployments and provide insights:
            {json.dumps(deployment_details, indent=2)}
            
            Include:
            1. Overall deployment health
            2. Replica status and scaling analysis
            3. Pod health and stability
            4. Update strategy effectiveness
            5. Performance recommendations
            """
            
            return await self._get_ai_analysis(analysis_prompt)
            
        except Exception as e:
            self.logger.error(f"Error fetching deployments: {str(e)}")
            raise

    async def get_cluster_health(self) -> str:
        """
        Comprehensive cluster health analysis
        
        Returns:
            str: AI-generated health analysis
        """
        try:
            health_data = {
                "nodes": await self._get_node_health(),
                "pods": await self._get_pod_health(),
                "services": await self._get_service_health(),
                "deployments": await self._get_deployment_health(),
                "system": await self._get_system_health()
            }

            analysis_prompt = f"""
            Analyze this Kubernetes cluster health data and provide a comprehensive assessment:
            {json.dumps(health_data, indent=2)}
            
            Include:
            1. Overall cluster health status
            2. Component-wise health analysis
            3. Resource utilization status
            4. Critical issues and warnings
            5. Performance bottlenecks
            6. Security concerns
            7. Optimization recommendations
            """
            
            return await self._get_ai_analysis(analysis_prompt)
            
        except Exception as e:
            self.logger.error(f"Error getting cluster health: {str(e)}")
            raise

    async def get_volume_status(self) -> str:
        """
        Fetch and analyze Kubernetes volume status
        
        Returns:
            str: AI-generated analysis of volume status
        """
        try:
            # Get PersistentVolumes
            pvs = self.core_v1.list_persistent_volume()
            # Get PersistentVolumeClaims
            pvcs = self.core_v1.list_persistent_volume_claim_for_all_namespaces()
            # Get StorageClasses
            storage_classes = self.storage_v1.list_storage_class()
            
            volume_data = {
                "persistent_volumes": [
                    {
                        "name": pv.metadata.name,
                        "capacity": pv.spec.capacity,
                        "access_modes": pv.spec.access_modes,
                        "status": pv.status.phase,
                        "storage_class": pv.spec.storage_class_name,
                        "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
                        "claim_ref": {
                            "name": pv.spec.claim_ref.name,
                            "namespace": pv.spec.claim_ref.namespace
                        } if pv.spec.claim_ref else None
                    } for pv in pvs.items
                ],
                "persistent_volume_claims": [
                    {
                        "name": pvc.metadata.name,
                        "namespace": pvc.metadata.namespace,
                        "status": pvc.status.phase,
                        "volume_name": pvc.spec.volume_name,
                        "storage_class": pvc.spec.storage_class_name,
                        "capacity": pvc.status.capacity if pvc.status.capacity else {},
                        "access_modes": pvc.spec.access_modes
                    } for pvc in pvcs.items
                ],
                "storage_classes": [
                    {
                        "name": sc.metadata.name,
                        "provisioner": sc.provisioner,
                        "reclaim_policy": sc.reclaim_policy,
                        "volume_binding_mode": sc.volume_binding_mode,
                        "allow_volume_expansion": sc.allow_volume_expansion if hasattr(sc, 'allow_volume_expansion') else None,
                        "parameters": sc.parameters
                    } for sc in storage_classes.items
                ]
            }

            analysis_prompt = f"""
            Analyze this Kubernetes volume status data and provide insights:
            {json.dumps(volume_data, indent=2)}
            
            Include:
            1. Overall storage health
            2. Capacity utilization
            3. Volume claim status
            4. Storage class usage
            5. Potential issues
            6. Performance recommendations
            """
            
            return await self._get_ai_analysis(analysis_prompt)
            
        except Exception as e:
            self.logger.error(f"Error getting volume status: {str(e)}")
            raise

    async def get_nodes(self) -> str:
        """
        Fetch and analyze Kubernetes nodes
        
        Returns:
            str: AI-generated analysis of nodes
        """
        try:
            nodes = self.core_v1.list_node()
            
            node_details = []
            for node in nodes.items:
                # Get pods running on this node
                pods = self.core_v1.list_pod_for_all_namespaces(
                    field_selector=f'spec.nodeName={node.metadata.name}'
                )
                
                node_info = {
                    "name": node.metadata.name,
                    "status": {
                        "conditions": [
                            {
                                "type": condition.type,
                                "status": condition.status,
                                "reason": condition.reason,
                                "message": condition.message
                            } for condition in node.status.conditions
                        ],
                        "capacity": node.status.capacity,
                        "allocatable": node.status.allocatable,
                        "node_info": {
                            "architecture": node.status.node_info.architecture,
                            "container_runtime": node.status.node_info.container_runtime_version,
                            "kernel": node.status.node_info.kernel_version,
                            "os": node.status.node_info.os_image,
                            "kubelet": node.status.node_info.kubelet_version
                        }
                    },
                    "pods": [
                        {
                            "name": pod.metadata.name,
                            "namespace": pod.metadata.namespace,
                            "phase": pod.status.phase,
                            "cpu_request": sum(
                                float(container.resources.requests['cpu'].replace('m', '')) / 1000 
                                if container.resources and container.resources.requests and 'cpu' in container.resources.requests 
                                else 0 
                                for container in pod.spec.containers
                            ),
                            "memory_request": sum(
                                float(container.resources.requests['memory'].replace('Mi', '')) 
                                if container.resources and container.resources.requests and 'memory' in container.resources.requests 
                                else 0 
                                for container in pod.spec.containers
                            )
                        } for pod in pods.items
                    ]
                }
                node_details.append(node_info)

            analysis_prompt = f"""
            Analyze these Kubernetes nodes and provide comprehensive insights:
            {json.dumps(node_details, indent=