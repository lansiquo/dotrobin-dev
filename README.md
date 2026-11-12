# dotrobin.dev

Robin Lansiquot's security portfolio: a static site in `site/`, served by GitHub Pages.

## Projects

| Project | What it does | Links |
|---|---|---|
| **sca-triage** v1.2.4 | npm SCA scanner (CLI on npm, and GitHub Action). Ranks vulnerable dependencies by whether your code imports them, applies the smallest safe upgrades, runs your tests and rescans. | [Case study](https://dotrobin.dev/sca-triage.html) · [Repo](https://github.com/lansiquo/sca-triage) · [npm](https://www.npmjs.com/package/sca-triage) |
| **sast-triage** v2.3 | Semgrep reviewer for Python, JavaScript and TypeScript (CLI and GitHub Action; GitHub App service prepared, not yet live). Labels findings new or pre-existing from the diff, ranks them P1–P3 and fails only on new P1s. | [Case study](https://dotrobin.dev/sast-triage.html) · [Repo](https://github.com/lansiquo/sast-triage) |

## Lab writeups

Academy, Blackpearl, Blue, Butler and Dev: isolated offline lab machines, each with an attack path, evidence screenshots and defensive findings. Evidence sources are tracked in [EVIDENCE.md](EVIDENCE.md).

## Local preview

```bash
python3 -m http.server 8788 --bind 127.0.0.1 --directory site
```
