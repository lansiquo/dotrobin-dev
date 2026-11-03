# Standalone portfolio demonstrations

[PR review walkthrough](https://dotrobin.dev/demos/pr.html) · [SCA evidence explorer](https://dotrobin.dev/demos/sca.html)

Only static HTML/CSS/JavaScript and curated JSON are deployed. No source evaluator, scanner service, credential, arbitrary input endpoint or localhost request exists.

PR examples were curated from the owner's current local showcase on November 3, 2026: four static analysis scenarios and six behavioral test scenarios. Source is displayed as inert text. The public walkthrough explains intended checks; it does not claim to run them.

SCA numbers come from the recorded November 3, 2026 baseline, Node 22.23.4/npm 10.9.9 on Linux: four direct dependencies, four audit findings before and zero after, seven functional tests passing per phase, and the minimist invariant failing before/passing after. Only minimist has demonstrated reachability. Findings are time bound and not a security certification.

Use a static HTTP server to preview these files. Data fetches are same site JSON; no external runtime dependencies are used.
