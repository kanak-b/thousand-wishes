#!/bin/sh

# Start MinIO server in the background
minio server /data --console-address ":9001" &

# Wait for MinIO to start
sleep 5

# Use env variables for credentials
MC_ALIAS_NAME="localminio"
MC_HOST="http://minio:9000"
MC_ACCESS_KEY="${MINIO_ROOT_USER}"
MC_SECRET_KEY="${MINIO_ROOT_PASSWORD}"

# Set mc alias using environment credentials
mc alias set "$MC_ALIAS_NAME" "$MC_HOST" "$MC_ACCESS_KEY" "$MC_SECRET_KEY"

# Create buckets if they don't exist
for bucket in clickstream users transactions; do
  if ! mc ls "${MC_ALIAS_NAME}/${bucket}" >/dev/null 2>&1; then
    echo "Creating bucket: $bucket"
    mc mb "${MC_ALIAS_NAME}/${bucket}"
  else
    echo "Bucket $bucket already exists"
  fi
done

# Keep container running
wait
