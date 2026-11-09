# Portfolio contribution guidance

## Lab writeups

- Call these pages **Writeups**, not penetration-testing reports, pentesting reports, or formal assessments. Update the page title, heading, description and cards consistently when adding a page. Formal reports are separate deliverables.
- Use `class="content article writeup"` and `writeups.css` for every lab writeup. Preserve the dark portfolio design, favicon, navigation and unrelated project content.
- Keep every writeup on the same layout: a `reading-layout` with the `reading-toc` "On this page" sidebar, a `class="environment"` target list, numbered `<h2>` sections, an `attack-path` diagram, and a `defense-panel` findings section. Match this structure when adding a page.
- Wrap every screenshot in `<figure class="evidence">` (styled frame and caption) with an inner `.evidence-scroll` region — never a bare `<figure>`, which `writeups.css` does not style. The figure may hold either a scrollable `<img>` or an `<a>` linking the full-size capture.
- Use high-contrast semantic `<pre><code>` panels for actual commands/output, with `tabindex="0"`, an accessible label, horizontal overflow and readable monospace text. Mark inline commands, account identities and paths with `<code>`.
- Preserve observed versus expected/reconstructed evidence. A screenshot of an elevated identity does not prove the entire exploitation mechanism. Never invent commands, results, screenshots, client work, or remediation that was performed.
- Prefer genuine matching screenshots from authorized lab notes. Inspect original pixels before selecting, crop irrelevant application chrome, remove metadata, and redact secrets or unrelated private content before publication. Do not generate synthetic terminal screenshots. Preserve originals unchanged.
- Keep only deliberately selected evidence files under `site/evidence/`. Never publish a whole vault, raw credential dumps, tokens, cookies or unrelated files. The owner explicitly authorized public disclosure of ordinary identifiers from these isolated offline labs on October 30, 2026. Preserve authentic lab IPs, usernames, hostnames, paths and system details in the selected evidence. Continue excluding actual passwords, tokens, cookies, private keys and unrelated personal data. Strip metadata. Keep source originals and private review galleries outside the repository. Do not fabricate missing values or evidence.
- Use responsive `<figure>`/`<img>` with intrinsic dimensions, meaningful alt text and a factual caption. Link to the original-size published image for legibility. Avoid duplicate captures. Keep command text selectable when available.
- If evidence is unavailable, keep the relevant caveat and use semantic text/code; do not claim expected output was captured. Consult `EVIDENCE.md` for current coverage.
- Validate balanced HTML, internal assets/links, screenshot dimensions, absence of sensitive incidental data, command preservation and scope. Verify the exact deployed commit and live HTTPS bytes after publishing. State when rendered browser QA was not performed.
- Never change DNS, HTTPS settings, account permissions or hosting providers as part of a content/style edit.
