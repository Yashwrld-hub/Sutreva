# Sutreva Session 50 — Historical Pattern Intelligence

## Purpose

Session 50 adds an advisory historical-context layer over the authoritative audit and engineering-intelligence results.

## Behavior

The layer consumes only prior review items with a closed/non-open disposition and matches them against current engineering exceptions by field and authoritative status.

It reports:

- number of similar reviewed cases;
- prior disposition distribution;
- most common prior disposition;
- number of prior projects/runs represented;
- pattern strength based on observed case count.

## Safety boundary

Historical matches are **not** approval rules. They never mutate:

- current audit status;
- current engineering severity;
- blocking state;
- configured template rules;
- evidence references.

This prevents historical behavior from silently becoming a compliance rule.

## UI

When reviewed history exists, the Audit Outcome area shows `Historical pattern intelligence` after the engineering exception table. A clear advisory note is displayed alongside the aggregate counters.

## Data source

The current implementation reads Sutreva's existing `ReviewItem` persistence model rather than introducing a second history database.

## Hackathon significance

This provides a concrete path toward a future feedback/evaluation loop: reviewed decisions can become structured context for future audits while remaining distinguishable from source evidence and deterministic engineering rules.
