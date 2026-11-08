# Standalone portfolio demonstrations

[PR review walkthrough](https://dotrobin.dev/demos/sast-triage.html) · [SCA evidence explorer](https://dotrobin.dev/demos/sca.html)

Only static HTML/CSS/JavaScript and curated JSON are deployed. No source evaluator, scanner service, credential, arbitrary input endpoint or localhost request exists.

PR examples were curated from the owner's local showcase: four static analysis scenarios and six behavioral test scenarios. Source is displayed as inert text. The public walkthrough explains intended checks; it does not claim to run them.

SCA numbers come from one recorded run of sca-triage on the repository's intentionally vulnerable lab app: four vulnerable direct dependencies before (3 × P1, 1 × P2) and zero after, 5/5 functional tests passing in both phases, and the minimist security test failing before and passing after. Only minimist has a demonstrated exploit. Findings are time-bound and not a security certification. The working tool is at https://github.com/lansiquo/sca-triage.

Use a static HTTP server to preview these files. Data fetches are same site JSON; no external runtime dependencies are used.
