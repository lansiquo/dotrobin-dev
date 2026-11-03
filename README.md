# dotrobin.dev

Robin Lansiquot’s static security portfolio. Public files live in `site/`; GitHub Pages serves them without a backend or home server.

## Interactive project demos

- [Pull Request Reviewer](https://dotrobin.dev/demos/pr.html): explore ten curated review examples and proposed fixes. Illustrative explanations only; no Python execution, Semgrep scan or GitHub action occurs in the browser.
- [SCA Remediation Lab](https://dotrobin.dev/demos/sca.html): switch between the saved November 3 four-dependency inventories and inspect recorded audit/security/functional-test results. This is a replay, not a fresh registry scan or test run.

These standalone demonstrations are separate from the real local applications. They accept no uploads and expose no backend or private infrastructure.

For a local portfolio preview, run `python3 -m http.server 8788 --bind 127.0.0.1 --directory site`, then open the printed loopback address. Stop with Ctrl-C.
