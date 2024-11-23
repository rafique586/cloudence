name: Pod Crash Investigation
description: Investigates pod crashes and restarts
version: 1.0

checks:
  - name: check_pod_logs
    description: Analyze pod logs for error patterns
    severity: HIGH
    patterns:
      - type: error
        regex: "exception|error|failure|failed"
      - type: crash
        regex: "crash|killed|terminated"
      - type: timeout
        regex: "timeout|timed out"

  - name: check_resource_usage
    description: Analyze resource usage patterns
    severity: HIGH
    thresholds:
      cpu_pressure: 80
      memory_pressure: 90
      disk_pressure: 85

automated_actions:
  - name: collect_crash_dumps
    description: Collect crash dumps and debug information
    action: collect_crash_dumps
    params:
      timeout_seconds: 300

  - name: analyze_restart_pattern
    description: Analyze pod restart patterns
    action: analyze_restart_pattern
    params:
      time_window_minutes: 60

recommendations:
  - condition: "crash_count > 3 in 1 hour"
    action: "Increase resource limits"
    description: "Pod is repeatedly crashing, might need more resources"

  - condition: "OOMKilled present in logs"
    action: "Adjust memory limits"
    description: "Pod is being killed due to memory pressure"
