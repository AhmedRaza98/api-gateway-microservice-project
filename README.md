# Project 3 - API Gateway Microservice Demo

This project implements a simple microservice architecture with a custom API gateway. The gateway centralizes routing, security, rate limiting, load balancing, and fault tolerance.

## Architecture

- **API Gateway**: single entry point for clients
- **Auth Service**: generates JWT tokens
- **Catalog Service**: two instances for load balancing
- **Order Service**: two instances for load balancing and failover

## Non-functional properties implemented

- **Security**: JWT authentication on protected routes
- **Rate limiting**: simple per-IP throttling at the gateway
- **Load balancing**: round-robin distribution across service replicas
- **Fault tolerance**: retry + failover + circuit breaker in the gateway
- **Scalability**: services run independently and can be replicated

## Run the project

```bash
docker compose up --build
```

The gateway is exposed on:

```text
http://localhost:8000
```