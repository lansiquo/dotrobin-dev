# Standalone portfolio demonstrations

[sast-triage demo](https://dotrobin.dev/demos/sast.html) · [sca-triage demo](https://dotrobin.dev/demos/sca.html)

Only static HTML/CSS/JavaScript and curated JSON are deployed. No source evaluator, scanner service, credential, arbitrary input endpoint or localhost request exists.

The sast-triage demo walks one simulated pull request through triage using ten curated OWASP Top 10:2025 examples from the owner's local showcase: four checked there by Semgrep demo rules and six by behavioral tests. Source is displayed as inert text. The browser page explains each check and runs none of them. The working reviewer is at https://github.com/lansiquo/sast-triage. The former addresses `pr.html` and `sast-triage.html` forward to `sast.html`.

The sca-triage demo replays one recorded run of sca-triage on sca-triage's intentionally vulnerable lab app: four vulnerable direct dependencies before (3 × P1, 1 × P2) and zero after, 5/5 functional tests passing in both phases, and the minimist security test failing before and passing after. Only minimist has a demonstrated exploit. Results describe that recorded run and are not a security certification. The working tool is at https://github.com/lansiquo/sca-triage.

Use a static HTTP server to preview these files. Data fetches are same site JSON; no external runtime dependencies are used.
