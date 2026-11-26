# ADR 0007: Managed-service prices are read from the provider's official page during the run

Date: 2026-11-27. Status: proposed

## Context
R15 (each managed service linked to its official pricing page with the date checked, or "to verify") and R7 (a
monthly cost estimate at the stated scale).

## Options

| Option | Fit | Cost | Effort | Lock-in | On failure |
|---|---|---|---|---|---|
| A. A list in the repo of **official pricing page URLs** per common service (not prices); during the run the model reads the page with its web fetch tool, and the price it uses is saved to the facts file with the URL and date | Prices are current; the list only holds links, which rarely change | Rs 0 | Low: keep the URL list current | None | Page unreadable or the price unclear: "to verify", and the estimate shows that part as unknown |
| B. A table of prices kept in the repo | Fast, offline | Rs 0 | High: stale within months | None | Wrong prices, silently |

## Decision
Option A. For a service not in the list, the model finds its official pricing page and the URL is recorded.
`validate.py` requires the URL and the date for every priced item. A price read from a page is marked as read by the
model, which is the one fact not fetched by a script, so `stack.md` shows "read from <URL> on <date>".

## Why
Current prices with a source the user can open, and no stale table to maintain.

## Revisit when
Providers publish machine-readable price APIs worth calling directly.
