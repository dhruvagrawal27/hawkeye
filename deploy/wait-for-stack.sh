#!/usr/bin/env bash
# Wait for all stack services to be healthy
set -euo pipefail

SERVICES=(
    "http://localhost:8000/healthz"
    "http://localhost:8080/"
    "http://localhost:8081/health/ready"
    "http://localhost:9090/-/healthy"
)

echo "Waiting for stack to be ready..."
for url in "${SERVICES[@]}"; do
    printf "  Waiting for %s " "$url"
    for i in $(seq 1 60); do
        if curl -sf "$url" >/dev/null 2>&1; then
            echo " ✓"
            break
        fi
        printf "."
        sleep 2
        if [ "$i" -eq 60 ]; then
            echo " ✗ TIMEOUT"
        fi
    done
done

echo "Stack is ready!"
