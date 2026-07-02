# Backend

Python modular monolith. Application code lands in Milestone 1; this tree currently holds the package skeleton only.

## Layout

```
src/vulnconsole/
├── contexts/       # 11 bounded contexts (see docs/architecture/service-decomposition.md)
│   └── <context>/  # each will contain domain/ application/ infrastructure/ api/
├── shared/         # shared kernel: event envelope, config, db session, pagination
└── platform/       # composition roots: api, worker, cli
```

Boundary rule (lint-enforced from Milestone 1 via import-linter): contexts never import another context's `domain` or `infrastructure`. Cross-context collaboration is NATS events or `application` interfaces only.
