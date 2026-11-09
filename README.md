# dotrobin.dev

Robin Lansiquot's security portfolio: a static site in `site/`, served by GitHub Pages.

## Projects

| Project | What it does | Links |
|---|---|---|
| **sca-triage** v1.2 | npm SCA scanner (CLI and GitHub Action). Ranks vulnerable dependencies by whether your code imports them, applies the smallest safe upgrades, runs your tests and rescans. | [Case study](https://dotrobin.dev/sca-triage.html) · [Repo](https://github.com/lansiquo/sca-triage) |
| **sast-triage** v1.0 | Semgrep pull request reviewer. Labels findings new or pre-existing, ranks them P1–P3 and fails the check only on new P1s. Runs locally and in its own CI; live GitHub deployment is prepared and not yet complete. | [Case study](https://dotrobin.dev/sast-triage.html) · [Demo](https://dotrobin.dev/demos/sast.html) · [Repo](https://github.com/lansiquo/sast-triage) |

The sast-triage demo runs entirely in the browser from curated data: it walks ten OWASP Top 10:2025 examples through triage. No backend, uploads or scanning.

## Lab write-ups

Academy, Blackpearl, Blue, Butler and Dev: isolated offline lab machines, each with an attack path, evidence screenshots and defensive findings. Evidence sources are tracked in [EVIDENCE.md](EVIDENCE.md).

## Local preview

```bash
python3 -m http.server 8788 --bind 127.0.0.1 --directory site
```
