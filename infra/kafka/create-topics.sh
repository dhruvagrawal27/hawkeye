#!/usr/bin/env bash
# Create Kafka topic if it doesn't exist
set -euo pipefail

BOOTSTRAP=${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}
TOPIC=${KAFKA_TOPIC:-hawkeye.events}

kafka-topics.sh \
  --bootstrap-server "$BOOTSTRAP" \
  --create --if-not-exists \
  --topic "$TOPIC" \
  --partitions 1 \
  --replication-factor 1

echo "Topic $TOPIC ready."
