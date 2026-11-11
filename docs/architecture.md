# Financial Harness architecture

The local and cloud demo can use the same Compose services. The AWS-style layout shows a possible EC2 deployment. The local stack starts without AWS.

```mermaid
flowchart TD
  User["Browser · React chat and charts"]
  Edge["HTTPS reverse proxy or AWS load balancer"]
  subgraph Host["AWS EC2 · Docker Compose"]
    API["FastAPI · frontend and job API"]
    Redis["Redis · queue, progress and saved results"]
    Worker["Celery · harness and MCP tools"]
    Sandbox["Python sandbox · no network"]
    API -->|"Submit and read jobs"| Redis
    Redis <-->|"Jobs, progress and results"| Worker
    Worker <-->|"Unix socket · data and result"| Sandbox
  end
  Providers["Alpha Vantage · saved Yahoo Finance snapshots as fallback"]
  User <-->|"Questions and answers"| Edge
  Edge <--> API
  Worker -->|"Fetch source data"| Providers
```

Redis stores job results for up to 24 hours. The calculation service runs as a non-root user with a read-only image, a memory limit, and a per-calculation timeout. Provider calls stay in the worker.
