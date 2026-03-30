#!/bin/bash
#
# Start the Master Control Commander demo.
# Launches: task broker, mock MCP server, health monitor, then the worker.
#
# Usage:
#   ./start_demo.sh          # Start everything
#   ./start_demo.sh --no-worker  # Start services only (run worker separately)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

BROKER_PORT="${BROKER_PORT:-8090}"
MCP_PORT="${MCP_PORT:-8091}"

cleanup() {
    echo ""
    echo "Shutting down demo services..."
    kill $BROKER_PID $MCP_PID $HEALTH_PID 2>/dev/null || true
    wait $BROKER_PID $MCP_PID $HEALTH_PID 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT

echo "=== Master Control Commander — Demo ==="
echo ""

# Check dependencies
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+."
    exit 1
fi

if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set."
    echo "  Copy .env.example to .env and add your key."
    exit 1
fi

# Start task broker
echo "[1/4] Starting task broker on port $BROKER_PORT..."
python3 -m uvicorn task_broker:app --port "$BROKER_PORT" --log-level warning &
BROKER_PID=$!
sleep 2

# Start mock MCP server
echo "[2/4] Starting mock MCP server on port $MCP_PORT..."
python3 -m uvicorn mock_mcp_server:app --port "$MCP_PORT" --log-level warning &
MCP_PID=$!
sleep 1

# Start health monitor
echo "[3/4] Starting health monitor..."
BROKER_URL="http://localhost:$BROKER_PORT" MCP_URL="http://localhost:$MCP_PORT" \
    python3 health_monitor.py &
HEALTH_PID=$!
sleep 2

if [ "$1" = "--no-worker" ]; then
    echo ""
    echo "Services running. Start the worker manually:"
    echo "  ANTHROPIC_API_KEY=sk-... python3 demo_worker.py"
    echo ""
    echo "Press Ctrl+C to stop services."
    wait
else
    # Start worker
    echo "[4/4] Starting demo worker..."
    echo ""
    BROKER_URL="http://localhost:$BROKER_PORT" MCP_URL="http://localhost:$MCP_PORT" \
        python3 demo_worker.py
fi
