#!/usr/bin/env bash
# Update mem0-server on Azure Container Apps to enable graph memory (Neo4j)
# Usage: NEO4J_PASSWORD=xxx ./infra/update-mem0-config.sh
#
# Run AFTER deploy-neo4j.sh
#
# mem0 server reads these env vars for graph config:
#   NEO4J_URI      → bolt://host:7687
#   NEO4J_USERNAME → neo4j
#   NEO4J_PASSWORD → <password>

set -euo pipefail

RESOURCE_GROUP="rg-mem0-prod"
NEO4J_PASSWORD="${NEO4J_PASSWORD:?Set NEO4J_PASSWORD env var}"

# Get Neo4j internal URL
echo "=== Finding Neo4j endpoint ==="
NEO4J_FQDN=$(az containerapp show \
    --name neo4j-graph \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)
NEO4J_URI="bolt://$NEO4J_FQDN:7687"
echo "  Neo4j: $NEO4J_URI"

# Update mem0-server with correct env vars (mem0 reads NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
echo "=== Updating mem0-server config ==="
az containerapp update \
    --name mem0-server \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars \
        "NEO4J_URI=$NEO4J_URI" \
        "NEO4J_USERNAME=neo4j" \
        "NEO4J_PASSWORD=secretref:neo4j-pw"

# Store password as a secret
az containerapp secret set \
    --name mem0-server \
    --resource-group "$RESOURCE_GROUP" \
    --secrets "neo4j-pw=$NEO4J_PASSWORD"

# Re-link env var to secret
az containerapp update \
    --name mem0-server \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars "NEO4J_PASSWORD=secretref:neo4j-pw"

echo ""
echo "=== Verifying ==="
MEM0_URL=$(az containerapp show \
    --name mem0-server \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)
echo "  mem0 URL: https://$MEM0_URL"
echo ""
echo "Waiting 30s for restart..."
sleep 30

# Health check
echo "=== Health check ==="
curl -s "https://$MEM0_URL/health" | python3 -m json.tool || echo "  Still starting up..."

echo ""
echo "=== Done ==="
echo "Graph memory is now enabled on mem0-server."
echo "New memories will automatically extract entities and relations."
echo ""
echo "Test in Claude Code:"
echo '  search_graph("test query")'
echo '  get_entities()'
echo '  get_relations()'
