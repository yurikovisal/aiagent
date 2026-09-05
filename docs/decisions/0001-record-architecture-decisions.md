# 1. Record architecture decisions

Date: 2026-09-05

## Status
Accepted

## Context
The master prompt calls for ADRs on significant decisions.

## Decision
Use lightweight ADRs (this format) under `docs/decisions/`, numbered
sequentially. Each significant, hard-to-reverse choice (data model shape,
LLM runtime, queue strategy, RAG boundary, approval-engine risk tiers) gets
one file.

## Consequences
Decisions are traceable without bloating `docs/architecture.md`.
