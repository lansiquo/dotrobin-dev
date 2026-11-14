# dotrobin.dev

Robin Lansiquot's security portfolio: a static site in `site/`, served by GitHub Pages.

Preview it locally:

```bash
python3 -m http.server 8788 --bind 127.0.0.1 --directory site
```

## Projects

- **sca-triage** v1.3.0: npm SCA scanner (CLI on npm, and GitHub Action). Ranks vulnerable dependencies by whether your code loads them, applies the smallest safe upgrades, runs your tests and rescans. [Case study](https://dotrobin.dev/sca-triage.html), [repo](https://github.com/lansiquo/sca-triage), [npm](https://www.npmjs.com/package/sca-triage).
- **sast-triage** v2.6.3: Semgrep reviewer for Python, JavaScript and TypeScript (CLI and GitHub Action; GitHub App service prepared, not yet live). Labels findings new or pre-existing from the diff, ranks them P1–P3 and fails only on new P1s. [Case study](https://dotrobin.dev/sast-triage.html), [repo](https://github.com/lansiquo/sast-triage).

## Lab writeups

Academy, Blackpearl, Blue, Butler and Dev: isolated offline lab machines, each with an attack path, evidence screenshots and defensive findings. Evidence sources: [EVIDENCE.md](EVIDENCE.md).

## Release data

Each deploy refreshes release data in the published copy, never the repository, so releases need no site change.

- **Release pulse.** The homepage header reads `site/data/pulse.json`. The deploy rebuilds it from the published releases of sast-triage and sca-triage. If GitHub is unreachable, the committed copy stays.
- **Version labels.** The deploy fills six elements marked `data-release` and `data-release-format`. Homepage: both project-card versions and the sast-triage card's GitHub Action snippet. sast-triage page: the two "Version X.Y" labels and the GitHub Action example.
- **Sources.** sast-triage: highest published `vX.Y.Z` GitHub release, no drafts or prereleases, from the rebuilt `site/data/pulse.json`. sca-triage: npm `dist-tags.latest` (what `npx sca-triage` runs), from `https://registry.npmjs.org/sca-triage`.
- **Fallback.** A label keeps its committed text if its version is unreadable or lower than that text. The deploy warns once and goes on. Unmarked text, like a note of which version something was checked on, is never rewritten.

The first line rebuilds the pulse. Both lines fill a local copy:

```bash
python3 .github/scripts/build_pulse.py site
python3 .github/scripts/build_versions.py site
```

## Site checks

The Site checks workflow runs on each pull request and push to `main`. It checks the pages, runs the scripts' unit tests, and scans the JavaScript in `site/` and Python in `.github/scripts/` with [sast-triage](https://github.com/lansiquo/sast-triage), pinned to a release's full commit. A pull request fails only on P1 findings it adds over its base branch. A push to `main` scans every file and fails on any P1.
