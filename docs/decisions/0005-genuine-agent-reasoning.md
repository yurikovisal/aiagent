# 5. Genuine LLM-driven agent reasoning (ReAct loop), with facts always grounded in tool results

Date: 2026-09-07

## Status
Accepted

## Context

The first version of every agent only ever called one or two hard-coded tools with parameters
pulled out of the request by a regex (in practice, just an order number). A free-text question
like "проверь наличие трубы 40x40x2, нужно 1800 кг к 8 сентября" never reached the actual
availability calculation, because nothing extracted "1800", "40x40x2" and the date from the
sentence — the user explicitly asked for "полноценная логика работы агентов" (agents that
actually reason, not scripted lookups).

## Decision

`meza/orchestrator/reasoning.py` implements a shared ReAct-style loop: the LLM is asked
(JSON-schema constrained via Ollama's structured output) to either call one of the agent's
allowed tools or finish, in a loop bounded by the same per-run `Budget` (§30) as everything
else. Every agent's `handle()` still keeps its original deterministic code path — cheap,
reliable — for the case where the router/params already give exact identifiers (an order
number, a material SKU); the reasoning loop only runs for genuinely free-text, ambiguous asks,
gated by a cheap keyword heuristic per agent so a broad "what needs attention" scan never pays
an LLM round-trip for domains that have nothing specific to interpret.

Critically, **the returned `AgentResult.summary`/`sources`/`data` are assembled from the tool
results, never from the LLM's own "finish" text.** This was not a theoretical concern: testing
against the local `qwen2.5:1.5b` model reproduced the LLM stating "no shortage" in its `finish`
summary immediately after its own tool call had returned `SHORTAGE` — a small model can call the
right tool and then still narrate the wrong conclusion. §9/§66/§73 are explicit that MEZA must
never invent data, so the free text is only ever used as phrasing, never as the source of a fact.

Three additional guardrails came out of testing this against the real local model, all in
`reasoning.py`:

1. **Forced first tool call.** A model will sometimes try to `finish` with a guessed answer on
   the very first step. `finish` is refused until at least one tool has actually been called.
2. **Working-memory parameter carry-over.** A model reliably picks the right *next* tool but
   sometimes drops a parameter (e.g. the material) it already established two steps earlier.
   Entity-like parameters (`material_sku`, `order_number`, `supplier_id`, ...) are remembered
   across the trajectory and auto-filled into a later call's schema if the model omits them —
   this is not new information, just context the model already provided once.
3. **Duplicate-call suppression.** A model can loop and call the same write tool (e.g.
   `create_purchase_request`) with identical parameters multiple times instead of recognizing
   the first call already succeeded. An identical `(tool, params)` call within one trajectory is
   refused rather than re-executed, so a chat turn can't silently produce three duplicate
   pending approvals for a human to sort out.

## Consequences

- A 1.5B local model reliably completes 2-step tool chains (e.g.
  `check_material_availability` → `create_purchase_request`) with correct parameter derivation
  (using the *computed* shortage quantity, not the user's originally stated quantity) after
  these guardrails and a worked few-shot example in the system prompt — verified end-to-end
  against the master prompt's shortage scenario (§52).
- It does not reliably get this right zero-shot without the guardrails; teams deploying a larger
  local model (§/docs/current-state.md notes the Mac mini can likely run something bigger) may be
  able to relax some of them, but removing the "ground summary in tool results" rule is not
  recommended regardless of model size — it is cheap insurance against a class of error that is
  otherwise invisible until a human reads a wrong number.
- Latency: each reasoning step is a full LLM round-trip (~5-15s on this CPU-only hardware), so a
  multi-step trajectory can take 20-60s. The per-agent keyword gating keeps broad "what needs
  attention" scans on the fast deterministic path; only genuinely targeted free-text questions
  pay the reasoning cost, and the UI streams operational status throughout (§42) so it never
  looks frozen.

## Addendum: the same grounding gap existed at the top-level synthesis, too

Date: 2026-09-08

While wiring Conversation Memory (§26) end-to-end, the same failure class documented above
turned up one level higher: `meza/orchestrator/core.py::synthesize()` — the final LLM call that
turns all domain agents' results into MEZA's one answer — is a different code path from the
per-agent reasoning loop, and it had no equivalent guard. Live-testing "Покажи склад" against
real (imported) low-stock materials produced: *"Извините, но я не могу предоставить информацию о
складе. В данный момент у меня нет доступа к данным о конкретных складских запасах."* — a flat
denial, immediately after the Warehouse agent had successfully returned two below-minimum
materials.

Fix: `synthesize()` now checks its own LLM output against a short list of denial/no-access
phrasings (`_denies_available_data`) and falls back to the deterministic join of domain
summaries — the same fallback already used when the LLM is unreachable — whenever the model
claims it has no data while `successful` (agent results that actually returned facts) is
non-empty. Confidence is scored lower (0.65) in that case so the UI's confidence label reflects
that the LLM's own phrasing was discarded.

This is the second time this exact failure mode was found by testing against the real model
rather than trusting the design on paper — worth remembering for any future LLM-facing code path
in MEZA: assume a small local model will occasionally narrate the opposite of its own inputs, and
grounding checks belong at every layer that turns tool/agent results into user-facing text, not
just the innermost one.
