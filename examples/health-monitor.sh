#!/bin/bash
# Health Monitor — Runs every 5 minutes via cron
# Produces a health.json consumed by workers and auto-stabilize
#
# Cron entry: */5 * * * * /path/to/health-monitor.sh

set -euo pipefail

HEALTH_FILE="/path/to/health.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- Check systemd services ---
check_service() {
    local name=$1
    local service=$2
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "\"$name\": {\"status\": \"green\", \"service\": \"$service\"}"
    else
        echo "\"$name\": {\"status\": \"red\", \"service\": \"$service\", \"error\": \"inactive\"}"
    fi
}

# --- Check HTTP endpoints ---
check_http() {
    local name=$1
    local url=$2
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [ "$http_code" = "200" ]; then
        echo "\"$name\": {\"status\": \"green\", \"http\": $http_code}"
    else
        echo "\"$name\": {\"status\": \"red\", \"http\": $http_code}"
    fi
}

# --- Check disk space ---
check_disk() {
    local usage
    usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    local status="green"
    [ "$usage" -gt 80 ] && status="yellow"
    [ "$usage" -gt 95 ] && status="red"
    echo "\"disk\": {\"status\": \"$status\", \"usage_percent\": $usage}"
}

# --- Check memory ---
check_memory() {
    local usage
    usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    local status="green"
    [ "$usage" -gt 85 ] && status="yellow"
    [ "$usage" -gt 95 ] && status="red"
    echo "\"memory\": {\"status\": \"$status\", \"usage_percent\": $usage}"
}

# --- Build health.json ---
# Customize these checks for your deployment
SERVICES=$(cat <<EOF
$(check_service "email-mcp" "email-mcp"),
$(check_service "erp-mcp" "erp-mcp"),
$(check_service "crm-mcp" "crm-mcp"),
$(check_service "business-worker" "business-worker"),
$(check_service "concierge-worker" "concierge-worker")
EOF
)

SYSTEM=$(cat <<EOF
$(check_disk),
$(check_memory)
EOF
)

cat > "$HEALTH_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "services": {
    $SERVICES
  },
  "system": {
    $SYSTEM
  }
}
EOF

echo "[$TIMESTAMP] Health check complete → $HEALTH_FILE"
