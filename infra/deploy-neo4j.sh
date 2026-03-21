#!/usr/bin/env bash
# Deploy Neo4j Community Edition to Azure Container Apps
# Usage: NEO4J_PASSWORD=xxx ./infra/deploy-neo4j.sh
#
# Prerequisites:
#   - az CLI logged in (az login)
#   - Existing resource group: rg-mem0-prod
#   - Existing Container Apps Environment (same as mem0-server)

set -euo pipefail

# ─── Config ───
RESOURCE_GROUP="rg-mem0-prod"
LOCATION="westeurope"
NEO4J_CONTAINER_NAME="neo4j-graph"
NEO4J_IMAGE="neo4j:5.26-community"
NEO4J_PASSWORD="${NEO4J_PASSWORD:?Set NEO4J_PASSWORD env var}"
STORAGE_ACCOUNT="stmem0prod"

# Get the Container Apps Environment from existing mem0-server
echo "=== Finding Container Apps Environment ==="
CA_ENV=$(az containerapp show \
    --name mem0-server \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.environmentId" -o tsv)
CA_ENV_NAME=$(echo "$CA_ENV" | rev | cut -d'/' -f1 | rev)
echo "  Environment: $CA_ENV_NAME"

# ─── Storage for Neo4j data persistence ───
echo "=== Creating storage for Neo4j data ==="

# Create storage account if not exists
az storage account show \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" 2>/dev/null || \
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)

# Create file share (10GB)
az storage share create \
    --name neo4j-data \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --quota 10 2>/dev/null || true

# Register storage with Container Apps Environment
az containerapp env storage set \
    --name "$CA_ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --storage-name neo4jstorage \
    --azure-file-account-name "$STORAGE_ACCOUNT" \
    --azure-file-account-key "$STORAGE_KEY" \
    --azure-file-share-name neo4j-data \
    --access-mode ReadWrite 2>/dev/null || true

# ─── Deploy Neo4j Container App ───
echo "=== Deploying Neo4j Container App ==="

# Create with YAML for proper volume mount + secret handling
cat > /tmp/neo4j-containerapp.yaml <<YAML
properties:
  environmentId: $CA_ENV
  configuration:
    ingress:
      external: false
      targetPort: 7687
      transport: tcp
    secrets:
      - name: neo4j-password
        value: "$NEO4J_PASSWORD"
  template:
    containers:
      - name: neo4j
        image: $NEO4J_IMAGE
        resources:
          cpu: 1.0
          memory: 2.0Gi
        env:
          - name: NEO4J_AUTH
            secretRef: neo4j-password
          - name: NEO4J_dbms_memory_heap_initial__size
            value: "512m"
          - name: NEO4J_dbms_memory_heap_max__size
            value: "1G"
          - name: NEO4J_dbms_memory_pagecache_size
            value: "256m"
        volumeMounts:
          - volumeName: neo4j-data
            mountPath: /data
    volumes:
      - name: neo4j-data
        storageType: AzureFile
        storageName: neo4jstorage
    scale:
      minReplicas: 1
      maxReplicas: 1
YAML

# Set the secret value to include the neo4j/ prefix for NEO4J_AUTH
# Neo4j expects NEO4J_AUTH=neo4j/<password>
cat > /tmp/neo4j-containerapp.yaml <<YAML
properties:
  environmentId: $CA_ENV
  configuration:
    ingress:
      external: false
      targetPort: 7687
      transport: tcp
    secrets:
      - name: neo4j-auth
        value: "neo4j/$NEO4J_PASSWORD"
  template:
    containers:
      - name: neo4j
        image: $NEO4J_IMAGE
        resources:
          cpu: 1.0
          memory: 2.0Gi
        env:
          - name: NEO4J_AUTH
            secretRef: neo4j-auth
          - name: NEO4J_dbms_memory_heap_initial__size
            value: "512m"
          - name: NEO4J_dbms_memory_heap_max__size
            value: "1G"
          - name: NEO4J_dbms_memory_pagecache_size
            value: "256m"
        volumeMounts:
          - volumeName: neo4j-data
            mountPath: /data
    volumes:
      - name: neo4j-data
        storageType: AzureFile
        storageName: neo4jstorage
    scale:
      minReplicas: 1
      maxReplicas: 1
YAML

az containerapp create \
    --name "$NEO4J_CONTAINER_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --yaml /tmp/neo4j-containerapp.yaml

rm -f /tmp/neo4j-containerapp.yaml

# Get the internal FQDN
echo ""
echo "=== Getting Neo4j endpoint ==="
NEO4J_FQDN=$(az containerapp show \
    --name "$NEO4J_CONTAINER_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)
echo "  Neo4j Bolt URL: bolt://$NEO4J_FQDN:7687"

echo ""
echo "=== Done ==="
echo "Neo4j deployed with:"
echo "  - Password stored as secret (not in env vars)"
echo "  - Persistent volume at /data (Azure Files)"
echo "  - Internal ingress only (not exposed to internet)"
echo "  - 1 vCPU, 2GB RAM, 1G heap"
echo ""
echo "Next: run ./infra/update-mem0-config.sh"
