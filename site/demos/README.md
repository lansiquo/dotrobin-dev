# Demos

[sast-triage demo](https://dotrobin.dev/demos/sast.html) · [sca-triage demo](https://dotrobin.dev/demos/sca.html)

Static HTML, CSS, JavaScript and JSON only: no scanner, backend, credentials or input endpoints.

- **sast-triage** (`sast.html`, `pr.js`, `pr-data.json`): one simulated pull request with ten OWASP Top 10:2025 examples, triaged with the real tool's ranking and gate rules. Source is shown as text and never run. `pr.html` and `sast-triage.html` forward here.
- **sca-triage** (`sca.html`, `sca.js`, `sca-data.json`): one recorded run on the lab app. Before: 4 vulnerable dependencies (3 × P1, 1 × P2) and the minimist security test failing. After: 0 vulnerable and all tests passing.
