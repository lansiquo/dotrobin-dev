# Portfolio contribution guidance

## Lab write-ups

- Call these pages **Write-ups**, not penetration-testing reports, pentesting reports, or formal assessments. Update the page title, heading, description and cards consistently when adding a page. Formal reports are separate deliverables.
- Use `class="content article writeup"` and `writeups.css` for every lab write-up. Preserve the Security Workbench design, favicon, navigation and unrelated project content.
- Use high-contrast semantic `<pre><code>` panels for actual commands/output, with `tabindex="0"`, an accessible label, horizontal overflow and readable monospace text. Mark inline commands, account identities and paths with `<code>`.
- Preserve observed versus expected/reconstructed evidence. A screenshot of an elevated identity does not prove the entire exploitation mechanism. Never invent commands, results, screenshots, client work, or remediation that was performed.
- Prefer genuine matching screenshots from authorized lab notes. Inspect original pixels before selecting, crop irrelevant application chrome, remove metadata, and redact secrets or unrelated private content before publication. Do not generate synthetic terminal screenshots. Preserve originals unchanged.
- Keep only deliberately selected evidence files under `site/evidence/`. Never publish a whole vault, raw credential dumps, tokens, cookies or unrelated files. Mask usernames, IP addresses, hostnames, identifying paths, system details and session identifiers using opaque pixel replacement. Strip metadata; audit text and captions for the same identifiers. Keep originals and private review galleries outside the repository. Clearly disclose redaction and placeholders.
- Use responsive `<figure>`/`<img>` with intrinsic dimensions, meaningful alt text and a factual caption. Link to the original-size published image for legibility. Avoid duplicate captures. Keep command text selectable when available.
- If evidence is unavailable, keep the relevant caveat and use semantic text/code; do not claim expected output was captured. Consult `EVIDENCE.md` for current coverage.
- Validate balanced HTML, internal assets/links, screenshot dimensions, absence of sensitive incidental data, command preservation and scope. Verify the exact deployed commit and live HTTPS bytes after publishing. State when rendered browser QA was not performed.
- Never change DNS, HTTPS settings, account permissions or hosting providers as part of a content/style edit.
