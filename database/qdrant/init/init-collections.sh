#!/bin/sh
set -eu

qdrant_url="${QDRANT_URL:-http://qdrant:6333}"
vector_size="${QDRANT_VECTOR_SIZE:-384}"

create_collection() {
  collection_name="$1"

  if curl --fail --silent "${qdrant_url}/collections/${collection_name}" >/dev/null 2>&1; then
    echo "Qdrant collection '${collection_name}' already exists."
    return
  fi

  curl --fail --silent --show-error \
    --request PUT \
    --header 'Content-Type: application/json' \
    --data "{\"vectors\":{\"size\":${vector_size},\"distance\":\"Cosine\"},\"on_disk_payload\":true}" \
    "${qdrant_url}/collections/${collection_name}"

  echo
  echo "Created Qdrant collection '${collection_name}'."
}

create_collection "risk_case_memory"
create_collection "risk_policies"

