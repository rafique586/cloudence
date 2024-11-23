# GCP Kubernetes Monitoring and Incident Management System

A comprehensive monitoring and incident management system for Kubernetes clusters running on Google Cloud Platform (GCP).

## Features

- Real-time monitoring of Kubernetes clusters
- Advanced metric collection and analysis
- Automated incident detection and management
- AI-powered troubleshooting assistance
- Extensible alert system
- Comprehensive logging and reporting

## Prerequisites

- Python 3.8+
- Google Cloud Platform account
- Kubernetes cluster on GKE
- Service account with necessary permissions

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/gcp-k8s-monitoring.git
cd gcp-k8s-monitoring

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Create a service account in GCP with the following roles:
   - Monitoring Viewer
   - Logging Viewer
   - Kubernetes Engine Viewer

2. Download the service account key JSON file

3. Set up environment variables:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
```

4. Configure the monitoring system:
```python
from src.gcp.config import setup_gcp_monitoring
setup_gcp_monitoring()
```

## Usage

### Basic Monitoring
```python
from src.monitoring.agent import MonitoringAgent

agent = MonitoringAgent(
    project_id="your-project-id",
    location="your-location",
    cluster_name="your-cluster"
)

# Start monitoring
agent.start_monitoring()
```

### Incident Management
```python
from src.incidents.manager import IncidentManager

incident_manager = IncidentManager(agent)
incident = await incident_manager.create_incident(
    issue_type="pod_crash",
    affected_components=["web-service"],
    severity="HIGH"
)
```

## Documentation

Detailed documentation is available in the `/docs` directory.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
