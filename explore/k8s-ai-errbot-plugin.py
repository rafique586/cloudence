"""
Errbot Plugin for Kubernetes AI Agent
Enables chat-based interaction with Kubernetes clusters through natural language
"""

from errbot import BotPlugin, botcmd, arg_botcmd
import asyncio
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
import json
from kubernetes_ai_agent import KubernetesAIAgent, QueryType

class KubernetesAIBot(BotPlugin):
    """
    Errbot plugin for Kubernetes cluster management using AI.
    Provides natural language interface for cluster operations through chat.
    """

    def activate(self):
        """
        Initialize the plugin and set up the K8s AI Agent
        """
        super().activate()
        
        # Initialize configuration
        self.config = {
            'k8s_context': self.plugin_dir / 'kubeconfig',
            'prometheus_url': self.bot_config.PROMETHEUS_URL if hasattr(self.bot_config, 'PROMETHEUS_URL') else None,
            'cache_timeout': 300,
            'allowed_users': getattr(self.bot_config, 'K8S_ALLOWED_USERS', []),
            'restricted_namespaces': getattr(self.bot_config, 'K8S_RESTRICTED_NAMESPACES', []),
        }
        
        try:
            # Initialize the K8s AI Agent
            self.k8s_agent = KubernetesAIAgent(
                context=self.config['k8s_context'],
                prometheus_url=self.config['prometheus_url'],
                cache_timeout=self.config['cache_timeout']
            )
            
            self.log.info("Kubernetes AI Bot activated successfully")
        except Exception as e:
            self.log.error(f"Failed to activate Kubernetes AI Bot: {str(e)}")
            raise

    def deactivate(self):
        """
        Cleanup when plugin is deactivated
        """
        super().deactivate()
        # Cleanup any open connections
        if hasattr(self, 'k8s_agent'):
            del self.k8s_agent

    def get_configuration_template(self):
        """
        Define configuration template for the plugin
        """
        return {
            'K8S_CONTEXT': '',
            'PROMETHEUS_URL': '',
            'CACHE_TIMEOUT': 300,
            'ALLOWED_USERS': [],
            'RESTRICTED_NAMESPACES': [],
        }

    def check_configuration(self, configuration: Dict[str, Any]) -> bool:
        """
        Verify plugin configuration
        """
        return True

    def _check_permissions(self, msg) -> bool:
        """
        Check if user has permission to execute commands
        
        Args:
            msg: Message object from Errbot
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        if not self.config['allowed_users']:
            return True
            
        user = msg.frm.nick
        return user in self.config['allowed_users']

    @botcmd
    def k8s_help(self, msg, args):
        """
        Show help information about available Kubernetes commands
        """
        help_text = """
        🤖 Kubernetes AI Bot Commands:
        
        1. Basic Queries:
           !k8s status - Show cluster status
           !k8s resources - Show resource usage
           !k8s events - Show recent events
        
        2. Natural Language Queries:
           !k8s ask <your question> - Ask anything about the cluster
           Example: !k8s ask how many pods are running in production namespace?
        
        3. Monitoring:
           !k8s metrics - Show cluster metrics
           !k8s alerts - Show active alerts
        
        4. Analysis:
           !k8s analyze - Analyze cluster health
           !k8s optimize - Get optimization recommendations
        
        5. Troubleshooting:
           !k8s troubleshoot - Get troubleshooting help
           !k8s diagnose <resource> - Diagnose specific resource
        
        6. Configuration:
           !k8s config show - Show current configuration
           !k8s config context - Show/change context
        
        Use !help <command> for more details about each command.
        """
        return help_text

    @botcmd(admin_only=True)
    def k8s_config(self, msg, args):
        """
        Show or modify bot configuration
        """
        if not args:
            return f"Current configuration:\n```\n{json.dumps(self.config, indent=2)}\n```"
            
        # Parse configuration commands
        try:
            cmd, *params = args.split()
            if cmd == 'set':
                key, value = params
                self.config[key] = value
                return f"Updated {key} = {value}"
            elif cmd == 'show':
                return f"Configuration:\n```\n{json.dumps(self.config, indent=2)}\n```"
        except Exception as e:
            return f"Error processing configuration: {str(e)}"

    @botcmd
    def k8s_status(self, msg, args):
        """
        Get current cluster status
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            status = asyncio.run(self.k8s_agent.check_cluster_health())
            return f"🔍 Cluster Status:\n```\n{status}\n```"
        except Exception as e:
            self.log.error(f"Error getting cluster status: {str(e)}")
            return f"❌ Error getting cluster status: {str(e)}"

    @botcmd
    def k8s_ask(self, msg, args):
        """
        Process natural language queries about the cluster
        
        Usage: !k8s ask how many pods are running in production namespace?
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        if not args:
            return "❓ Please provide a question about the cluster"
            
        try:
            response = asyncio.run(self.k8s_agent.process_natural_language_query(args))
            return f"🤖 Answer:\n{response}"
        except Exception as e:
            self.log.error(f"Error processing query: {str(e)}")
            return f"❌ Error processing query: {str(e)}"

    @botcmd
    def k8s_analyze(self, msg, args):
        """
        Perform comprehensive cluster analysis
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            analysis = asyncio.run(self.k8s_agent.analyze_cluster())
            return f"📊 Cluster Analysis:\n```\n{analysis}\n```"
        except Exception as e:
            self.log.error(f"Error analyzing cluster: {str(e)}")
            return f"❌ Error analyzing cluster: {str(e)}"

    @botcmd
    def k8s_troubleshoot(self, msg, args):
        """
        Get troubleshooting recommendations
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            issues = asyncio.run(self.k8s_agent.troubleshoot_cluster_issues())
            return f"🔧 Troubleshooting Results:\n```\n{issues}\n```"
        except Exception as e:
            self.log.error(f"Error troubleshooting: {str(e)}")
            return f"❌ Error during troubleshooting: {str(e)}"

    @botcmd
    def k8s_metrics(self, msg, args):
        """
        Show cluster metrics
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            metrics = asyncio.run(self.k8s_agent.get_performance_metrics())
            return f"📈 Cluster Metrics:\n```\n{metrics}\n```"
        except Exception as e:
            self.log.error(f"Error getting metrics: {str(e)}")
            return f"❌ Error getting metrics: {str(e)}"

    @arg_botcmd('resource', type=str)
    def k8s_diagnose(self, msg, resource):
        """
        Diagnose specific resource issues
        
        Usage: !k8s diagnose deployment/myapp
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            diagnosis = asyncio.run(self.k8s_agent.diagnose_resource(resource))
            return f"🔍 Diagnosis for {resource}:\n```\n{diagnosis}\n```"
        except Exception as e:
            self.log.error(f"Error diagnosing resource: {str(e)}")
            return f"❌ Error diagnosing resource: {str(e)}"

    @botcmd
    def k8s_optimize(self, msg, args):
        """
        Get optimization recommendations
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            recommendations = asyncio.run(self.k8s_agent.analyze_cost_optimization())
            return f"💡 Optimization Recommendations:\n```\n{recommendations}\n```"
        except Exception as e:
            self.log.error(f"Error getting optimization recommendations: {str(e)}")
            return f"❌ Error getting recommendations: {str(e)}"

    @botcmd
    def k8s_alerts(self, msg, args):
        """
        Show active alerts
        """
        if not self._check_permissions(msg):
            return "⛔ You don't have permission to execute this command"
            
        try:
            alerts = asyncio.run(self.k8s_agent.get_active_alerts())
            return f"🚨 Active Alerts:\n```\n{alerts}\n```"
        except Exception as e:
            self.log.error(f"Error getting alerts: {str(e)}")
            return f"❌ Error getting alerts: {str(e)}"

