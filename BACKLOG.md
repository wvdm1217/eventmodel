# Project Backlog

| Priority | Category | Task | Status |
|---|---|---|---|
| High | Core Framework | Add Dependency Injection support for service handlers (e.g., passing DB sessions or API clients) | Draft |
| High | Core Framework | Add graceful shutdown hook (`stop()`) for `Service` instances in `App` | Draft |
| High | Testing | Add testing utilities (e.g. `TestApp` / `TestBroker`) for mocking services and inspecting event emissions | Draft |
| Medium | Broker Adapters | Implement generic message broker adapters (Kafka/Redis/RabbitMQ) | Draft |
| Medium | Error Handling | Implement Error Handling and Dead Letter Queue (DLQ) support in service wrapper | Draft |
| Medium | Error Handling | Add support for automatic retries with exponential backoff on event processing failures | Draft |
| Medium | Observability | Add OpenTelemetry / Distributed Tracing support for tracking event flows | Draft |
| Medium | Core Framework | Add concurrency control (e.g., max concurrent executions) for event consumption | Draft |
| Medium | Documentation | Initialize MkDocs/Sphinx for `docs.eventmodel.app` source code documentation | Draft |
| Low | Interoperability | Add support for the CloudEvents specification | Draft |
| Low | Core Framework | Add static return-type validation in the `@service` decorator at module import time | Draft |
