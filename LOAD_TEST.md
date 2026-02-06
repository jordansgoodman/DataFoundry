# Capacity / Load Testing

## Goals
- Validate single-node throughput
- Establish baseline concurrency limits

## Suggested Approach
- Use a lightweight HTTP load tester (k6, vegeta, or Locust)
- Focus on DataFoundry BI dashboard endpoints and Airflow UI pages

## Minimal Plan
1. Pick 2–3 dashboards and a SQL Lab query.
2. Simulate 25/50/100 concurrent users for 10–15 minutes.
3. Track response time, error rate, and CPU/memory usage.

## What Good Looks Like
- P95 response time under 2–5 seconds
- Error rate < 1%
- No sustained CPU > 90% for 10+ minutes

## Notes
- Increase Postgres resources if dashboards are slow.
- Reduce DataFoundry BI concurrency if memory pressure occurs.
