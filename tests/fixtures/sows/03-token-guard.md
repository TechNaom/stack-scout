# Statement of Work: Token Guard

## 1. Background

The client is a small software company whose products call several large
language model APIs. Spending on these calls has grown fast and without
warning: one runaway job last quarter spent a month's budget in a weekend.
The client wants a gateway that sits between its applications and the model
providers, counts tokens and cost per team and per key, and stops calls when
a limit is reached.

The client intends to package Token Guard and sell it to its own customers as
a self-hosted product, so every component we choose must have a licence that
allows redistribution inside a commercial product.

There are no names to keep private in this document; it may be shared
openly, including in public searches and issues.

## 2. Scope

In scope:

- An HTTP proxy that accepts requests in the providers' API formats and
  forwards them.
- Token counting and cost calculation for each request and response,
  including streamed responses.
- Budgets and rate limits per team, per API key and per model.
- A dashboard of spend over time with drill-down by team and model.
- Alerts by email and chat webhook when spend passes 50, 80 and 100 percent
  of a budget.

Out of scope: prompt caching, response quality evaluation, and billing the
client's own customers.

## 3. Requirements

1. R1. Proxy requests to at least three model providers without changing the
   request or response bodies.
2. R2. Count input and output tokens for every request, including streamed
   responses, and price them from a configurable price table.
3. R3. Reject a request with a clear error once its team, key or model budget
   is used up; never forward it.
4. R4. Add no more than 20 milliseconds of latency to a request at the
   median.
5. R5. Store usage records for 13 months for reporting.
6. R6. Show spend per day, team, key and model on a dashboard.
7. R7. Send alerts at 50, 80 and 100 percent of each budget.
8. R8. Ship as a container image with a single configuration file.

## 4. Technical context

The client's engineers write TypeScript on Node.js, and the product must be
written in TypeScript so they can extend it. The client will spend no more
than $150 a month on hosting its own internal instance during the pilot.

## 5. Gaps and questions for the client

- Where will the client's own instance run, and which cloud or hosting
  platforms must the self-hosted product support for customers?
- How many requests per second must one instance handle, and how many teams,
  keys and customers should we plan for?
- Should budgets reset monthly, weekly, or on a schedule each team chooses?
- Which chat tools must the alert webhook support first?
- Is there a preferred database for usage records, or is that our choice?

## 6. Deliverables and timeline

A working gateway and dashboard in six weeks, a container image, a sample
configuration file, and installation notes written for the client's
customers.
