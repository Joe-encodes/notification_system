{
  "version": "1.0",
  "rules": [
    {
      "id": "no-random-file-creation",
      "description": "Do not create new files unless the task explicitly requires it. Modify existing files or referenced modules where relevant."
    },
    {
      "id": "understand-system-flow",
      "description": "Before suggesting any code, map the logical flow between microservices: API Gateway, User, Email, Push, and Template. Understand which service owns which logic."
    },
    {
      "id": "respect-async-design",
      "description": "All notification operations between services must be asynchronous via RabbitMQ or Kafka queues. Never use direct REST calls for message delivery or retries."
    },
    {
      "id": "reuse-existing-code",
      "description": "Always check for reusable modules (utils, services, config, constants, or middleware) before creating new implementations."
    },
    {
      "id": "simulate-runtime",
      "description": "Mentally dry-run each workflow—API request to message queue to worker processing—to anticipate runtime or logic issues before writing or editing code."
    },
    {
      "id": "micro-to-macro-workflow",
      "description": "Work from small, tested components (e.g., queue listener, retry handler) to larger integrated flows. Confirm each layer works before connecting them."
    },
    {
      "id": "circuit-breaker-awareness",
      "description": "When writing code that depends on external services (SMTP, FCM, etc.), include fallback logic or circuit breaker patterns to prevent total failure."
    },
    {
      "id": "idempotency-enforcement",
      "description": "Ensure idempotent behavior for message processing using request IDs or unique message keys. Avoid duplicate notifications."
    },
    {
      "id": "naming-standard",
      "description": "Use snake_case consistently for request, response, and model names. Maintain schema alignment across services."
    },
    {
      "id": "ci-cd-awareness",
      "description": "When modifying or generating files, ensure they align with the defined CI/CD pipeline and Docker-based deployment structure."
    },
    {
      "id": "system-stability",
      "description": "Prioritize stable, production-ready logic over unnecessary refactoring or style changes. Avoid breaking existing integrations."
    }
  ]
}

