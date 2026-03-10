#!/bin/bash
set -e
# Hadoop Streaming with Python mapper/reducer. Logs to S3 for debugging.

LOG=/tmp/emr-streaming.log
exec 1> >(tee -a "$LOG") 2>&1

echo "=== Finding hadoop-streaming.jar ==="
STREAMING_JAR=/usr/lib/hadoop-mapreduce/hadoop-streaming.jar
if [ ! -f "$STREAMING_JAR" ]; then
  STREAMING_JAR=$(find /usr -name 'hadoop-streaming*.jar' 2>/dev/null | head -1)
fi
if [ -z "$STREAMING_JAR" ]; then
  echo "ERROR: hadoop-streaming.jar not found"
  exit 1
fi
echo "Using: $STREAMING_JAR"

echo "=== Removing existing output (if any) ==="
hadoop fs -rm -r s3://lab2-twitter-stats/output/ 2>/dev/null || true

echo "=== Running Hadoop Streaming ==="
hadoop jar "$STREAMING_JAR" \
  -files s3://lab2-twitter-stats/scripts/mapper.py,s3://lab2-twitter-stats/scripts/reducer.py \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" \
  -input s3://lab2-twitter-stats/input/ \
  -output s3://lab2-twitter-stats/output/

echo "=== Done ==="
# Upload log to S3 so you can read the error if something fails
hadoop fs -put -f "$LOG" s3://lab2-twitter-stats/logs/emr-streaming.log 2>/dev/null || true
