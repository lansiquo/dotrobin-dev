# dotrobin.dev

Robin Lansiquot’s static security portfolio. Public files live in `site/`; GitHub Pages serves them without a backend or home server.

## Project status

- **sca-triage: Version 1.0.** An npm SCA scanner, run from the command line or as a GitHub Action. It scans dependencies, ranks findings by import evidence, applies the proposed upgrades, runs the project's tests, rescans and saves before-and-after evidence. CI runs the full lab workflow on every push to `main` and every pull request. See the [case study](https://dotrobin.dev/sca-triage.html) and the [repository](https://github.com/lansiquo/sca-triage).
- **sast-triage: Version 1.0.** A Semgrep pull request reviewer that labels each finding new or pre-existing, ranks it P1–P3 and fails the check only on new P1 findings. It runs locally and in its own CI; live GitHub deployment is prepared and not yet complete. See the [case study](https://dotrobin.dev/sast-triage.html) and the [repository](https://github.com/lansiquo/sast-triage).

## Interactive project demos

- [sast-triage demo](https://dotrobin.dev/demos/sast.html): watch sast-triage triage one simulated pull request with ten curated OWASP Top 10:2025 examples, then inspect each example's proposed fix. A guided walkthrough built from curated data; no Python, Semgrep scan or GitHub request runs in the browser.
- [sca-triage demo](https://dotrobin.dev/demos/sca.html): step through one recorded sca-triage run on the lab app, before and after upgrades, with its scan summary, security test and full test results. A replay of a real run; nothing is installed or scanned in the browser.

The demos are static pages, separate from the working tools. They accept no uploads and expose no backend or private infrastructure. The former demo addresses `/demos/pr.html` and `/demos/sast-triage.html` forward to `/demos/sast.html`.

For a local portfolio preview, run `python3 -m http.server 8788 --bind 127.0.0.1 --directory site`, then open the printed loopback address. Stop with Ctrl-C.
