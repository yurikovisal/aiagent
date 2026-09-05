# 2. Run natively instead of Docker Compose in this environment

Date: 2026-09-05

## Status
Accepted

## Context
Phase 0 audit found the Docker *daemon* unavailable in this container
(client binary present, `/var/run/docker.sock` absent). PostgreSQL, Redis,
Python and Node are installed natively and usable directly.

## Decision
Primary local dev/run path uses native processes managed by `make`/scripts.
`docker-compose.yml` is still authored and kept in sync for hosts (including
the target Mac mini) where the Docker daemon is available — it is not
removed or left to rot.

## Consequences
`make dev` does not depend on Docker. Anyone with Docker available can still
run `docker compose up` and get the same system.
