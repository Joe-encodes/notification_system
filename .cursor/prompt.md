### Prompt: Distributed Notification System (Stage 4 HNG Backend)

You are assisting in building a **Distributed Notification System** composed of multiple microservices:

* **API Gateway:** entry point, authentication, and routing.
* **User Service:** manages user data and preferences.
* **Email Service:** sends templated emails.
* **Push Service:** sends mobile/web push notifications.
* **Template Service:** manages message templates and localization.

The system communicates **asynchronously** through RabbitMQ or Kafka.
Each service has its **own database**, with **PostgreSQL + Redis** for caching, rate limiting, and idempotency tracking.

#### Your guiding principles:

1. **No random file creation.** Always use and modify existing structures unless explicitly asked otherwise.

2. **Dry-run mentally.** Trace how a request flows across services before writing code. Anticipate runtime issues, retries, and async failures.

3. **Follow microservice boundaries.** Don't blend concerns (e.g., the Email Service should not directly access User DBs — use message queues or REST endpoints).

4. **Ensure idempotency.** Avoid sending duplicate notifications by respecting unique `request_id`s.

5. **Integrate circuit breakers and retry logic.** Handle service downtime gracefully.

6. **Prioritize async resilience.** Any message loss or queue block should trigger a dead-letter or retry mechanism.

7. **Confirm flow before coding.** Understand how your edits fit into the distributed flow (request → validation → queue → processing → status update).

8. **Be environment-aware.** Respect CI/CD workflows, Docker configs, and deployment constraints.

9. **Use snake_case for all schema names.**

10. **Think like a systems engineer.** Every change must make sense in the full distributed context — not just inside a single file.

Before implementing anything, reason through it logically, validate dependencies, confirm flow integrity, and optimize the code path.



