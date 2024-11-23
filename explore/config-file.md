# GCP Configuration
gcp:
  project_id: your-project-id
  location: your-location
  cluster_name: your-cluster-name
  credentials_path: path/to/service-account-key.json

# Monitoring Configuration
monitoring:
  interval_seconds: 60
  metrics:
    - cpu
    - memory
    - disk
    - network
    - pod_health
  retention_days: 30

# Alerting Configuration
alerting:
  default_threshold:
    cpu: 80
    memory: 90
    disk: 85
  notification:
    webhook_url: https://your-webhook-url
    email: alerts@your-domain.com

# Incident Management
incident_management:
  auto_create: true
  auto_investigate: true
  playbooks_path: config/playbooks
  severity_levels:
    - CRITICAL
    - HIGH
    - MEDIUM
    - LOW

# Logging Configuration
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: logs/monitoring.log
  max_size_mb: 100
  backup_count: 5
