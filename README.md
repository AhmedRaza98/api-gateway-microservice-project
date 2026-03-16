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

## Demo steps

### 1. Verify the gateway is up

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

### 2. Show security

This must fail because no JWT token is sent:

```bash
curl http://localhost:8000/catalog/products
```

### 3. Obtain a token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Copy the `access_token` value.

### 4. Show load balancing

Run the next command several times. The `instance` field alternates between `catalog-service-1` and `catalog-service-2`.

```bash
TOKEN=<paste_token_here>
curl http://localhost:8000/catalog/products \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Create and read orders

```bash
curl -X POST http://localhost:8000/orders/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":2}'

curl http://localhost:8000/orders/all \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Show fault tolerance

Stop one order instance:

```bash
docker stop order-service-1
```

Repeat this request. The gateway retries another replica and the request still succeeds.

```bash
curl http://localhost:8000/orders/all \
  -H "Authorization: Bearer $TOKEN"
```

You can inspect gateway behaviour here:

```bash
curl http://localhost:8000/metrics
```

### 7. Show total failure

Stop both order instances:

```bash
docker stop order-service-1 order-service-2
```

Now the gateway returns:

- `503 Service Unavailable`

That demonstrates graceful degradation instead of client-side confusion.

## Why the API gateway is better than direct client-to-service calls

Without the gateway:

- clients need to know all service addresses
- authentication must be duplicated in each service
- rate limiting must be implemented in each service
- service discovery/load balancing logic leaks into clients
- fault handling becomes inconsistent

With the gateway:

- one public endpoint
- centralized security policy
- centralized traffic control
- transparent load balancing and failover
- simpler clients and easier maintenance
