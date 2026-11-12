# dotrobin.dev

Robin Lansiquot's security portfolio: a static site in `site/`, served by GitHub Pages.

## Projects

| Project | What it does | Links |
|---|---|---|
| **sca-triage** v1.2.4 | npm SCA scanner (CLI on npm, and GitHub Action). Ranks vulnerable dependencies by whether your code imports them, applies the smallest safe upgrades, runs your tests and rescans. | [Case study](https://dotrobin.dev/sca-triage.html) · [Repo](https://github.com/lansiquo/sca-triage) · [npm](https://www.npmjs.com/package/sca-triage) |
| **sast-triage** v2.4 | Semgrep reviewer for Python, JavaScript and TypeScript (CLI and GitHub Action; GitHub App service prepared, not yet live). Labels findings new or pre-existing from the diff, ranks them P1–P3 and fails only on new P1s. | [Case study](https://dotrobin.dev/sast-triage.html) · [Repo](https://github.com/lansiquo/sast-triage) |

## Lab writeups

Academy, Blackpearl, Blue, Butler and Dev: isolated offline lab machines, each with an attack path, evidence screenshots and defensive findings. Evidence sources are tracked in [EVIDENCE.md](EVIDENCE.md).

## Release pulse data

The release pulse in the homepage header reads `site/data/pulse.json`. Every deploy rebuilds that file from the published releases of sast-triage and sca-triage, so the committed copy is only the fallback for a deploy that cannot reach GitHub. To rebuild it locally:

```bash
python3 .github/scripts/build_pulse.py site
```

## Version labels

Every deploy also writes the current versions into the pages it publishes, so the site needs no change after a release. It fills each element marked with `data-release` and `data-release-format`, six labels in all: on the homepage, the version on the two project cards and the version in the sast-triage card's GitHub Action snippet, and, on the sast-triage page, the two "Version X.Y" labels and the version in the GitHub Action example.

| Tool | Version shown | Read from |
|---|---|---|
| sast-triage | The highest published GitHub release tagged `vX.Y.Z`, without drafts and prereleases | `site/data/pulse.json`, which the same deploy has just rebuilt |
| sca-triage | `dist-tags.latest` on npm, the version `npx sca-triage` runs | `https://registry.npmjs.org/sca-triage` |

Only the deployed copy changes, never the repository. The committed text is the fallback: a label keeps it when its version cannot be read or is lower than the committed one, and the deploy goes on with one warning. Text without the two attributes, such as a note that says which version something was checked on, is never rewritten. To fill a local copy:

```bash
python3 .github/scripts/build_pulse.py site
python3 .github/scripts/build_versions.py site
```

## Site checks

Every pull request and every push to `main` runs the Site checks workflow. Besides checking the pages and running the scripts' unit tests, it scans the site's code, the JavaScript in `site/` and the Python scripts in `.github/scripts/`, with [sast-triage](https://github.com/lansiquo/sast-triage), pinned to the full commit of a release. A pull request is compared with its base branch and fails only on a P1 finding it adds. A push to `main` scans every file, and any P1 finding fails that run.

## Local preview

```bash
python3 -m http.server 8788 --bind 127.0.0.1 --directory site
```
