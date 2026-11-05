# dotrobin.dev

Robin Lansiquot’s static security portfolio. Public files live in `site/`; GitHub Pages serves them without a backend or home server.

## Project status

- **sca-triage: functional end-to-end.** The local CLI and GitHub Action implement dependency scanning, import-based prioritization, upgrade application, project tests, a fresh scan and saved evidence. The lab workflow is exercised in CI. See the [case study](https://dotrobin.dev/sca-remediation.html).
- **sast-triage: in development.** The local review demo works; the broader service remains in development. Its triage step (new vs pre-existing findings, P1–P3 ranking) is planned, not built yet. No live deployment is claimed. See the [project page](https://dotrobin.dev/pr-reviewer.html).

These labels describe the tools. The browser demos below are separate static presentations.

## Interactive project demos

- [sast-triage](https://dotrobin.dev/demos/pr.html): explore ten curated review examples and proposed fixes. Illustrative explanations only; no Python execution, Semgrep scan or GitHub action occurs in the browser.
- [sca-triage](https://dotrobin.dev/demos/sca.html): switch between the recorded four-dependency inventories and inspect recorded audit/security/functional-test results. This is a replay, not a fresh registry scan or test run.

These standalone demonstrations are separate from the real local applications. They accept no uploads and expose no backend or private infrastructure.

For a local portfolio preview, run `python3 -m http.server 8788 --bind 127.0.0.1 --directory site`, then open the printed loopback address. Stop with Ctrl-C.
