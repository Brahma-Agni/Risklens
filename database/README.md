# Database infrastructure

This directory contains versioned initialization assets for the RiskLens data
stores.

## PostgreSQL

`postgres/init` is mounted at `/docker-entrypoint-initdb.d`. PostgreSQL runs the
scripts in filename order only when the database volume is first created.

## Neo4j

`neo4j/init/constraints.cypher` defines graph uniqueness constraints and lookup
indexes. The `neo4j-init` one-shot container applies it after Neo4j is healthy.

## Qdrant

`qdrant/init/init-collections.sh` idempotently creates:

- `risk_case_memory` for resolved analyst cases
- `risk_policies` for embedded demo policy documents

Both collections default to 384-dimensional cosine vectors. Set
`QDRANT_VECTOR_SIZE` before first startup if a different embedding model is
planned. A collection's vector size cannot be changed without recreating or
migrating it.

