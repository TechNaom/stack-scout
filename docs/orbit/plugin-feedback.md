# Idea to Orbit: plugin feedback (from Stack Scout)

- 2026-11-27 · ignite · Missing: a cold read before the Ignite gate. An outside review of the first brief and PRD
  (8/10) found five real gaps the Ignite steps did not prompt for: a non-interactive mode when another tool calls
  the product, managed services (not only libraries) and their prices, whether the picks fit together, security
  health (known vulnerabilities, releases, contributors), and confidential input leaking into search queries.
  Better: run the Blueprint's cold-read brief on the brief and PRD too, before asking for the Ignite yes.
- 2026-11-27 Assemble: two cold reads found what Blueprint missed: how the code finds its own files under each install path (plugin vs script), what starts and ends a run, `python` vs `python3`, and Windows line endings/encoding. Suggest Blueprint red flags: "How does the code find its own files on every install path?" and "What starts and ends one run, and what state survives between runs?"
