# Shared contracts

`shared` contains language-neutral API and event contracts used at boundaries
between independently implemented services. It is not a running container and
must not contain business logic or service-specific models.

Current contracts:

- `schemas/transaction-request.schema.json`: generator/frontend to backend
- `schemas/risk-evaluation.schema.json`: backend to risk service and back
- `schemas/evaluation-label.schema.json`: generator truth consumed only by evaluation
- `schemas/stream-result.schema.json`: generator streaming result consumed by evaluation

Java records, Python Pydantic models, and TypeScript types remain local to their
services. These schemas are the reviewable source for compatibility tests and
future code generation. Keeping ground-truth schemas here does not expose labels
to runtime scoring; only the offline evaluation tool reads label files.
