# Write-up evidence

`site/evidence/` holds 20 screenshots: the 12 Blackpearl, Blue and Butler captures in the table below, and 4 Academy and 4 Dev captures listed in their sections. The sca-triage case study uses no screenshots (see "sca-triage case study"). The 12 tabled screenshots are authentic selected crops from the isolated offline lab. The owner explicitly authorized public disclosure of ordinary lab IPs, usernames, hostnames and system details. The selected unmasked copies were visually inspected before restoration; no passwords, tokens, cookies or private keys were visible in this set. PNG metadata is stripped. Source originals remain outside this repository. No generated terminal imagery is used. The Blue options capture retains its application-chrome crop.

| Public image | Original capture timestamp | Content |
| --- | --- | --- |
| blackpearl-cms-options.png | 20261025104845 | Navigate CMS target/callback/virtual host configuration |
| blackpearl-foothold.png | 20261025105102 | Shell and www-data identity |
| blackpearl-pty.png | 20261025105539 | Python PTY invocation |
| blackpearl-local-checks.png | 20261025105609 | sudo unavailable; history |
| blackpearl-transfer.png | 20261025110024 | HTTP transfer on port 80; prose corrected from 8000 to match capture |
| blackpearl-linpeas.png | 20261025110007 | chmod and LinPEAS execution |
| blackpearl-root.png | 20261025112822 | PHP invocation and root identity |
| blue-os-discovery.png | 20261021125528 | SMB Windows 7 SP1 identification |
| blue-exploit-options.png | 20261021125302 | Exact pixel crop x=0, y=256, width=881, height=177; removes application chrome |
| blue-system.png | 20261021125129 | Session opening, getuid and sysinfo |
| butler-service-check.png | 20261024142918 | Service state and start attempt |
| butler-system.png | 20261024143009 | Callback and SYSTEM identity |

## Gaps and exclusions

- Blackpearl: no selected captures for DNSRecon/getent/curl results, the filtered 652-byte FFUF result, TARGETURI setup, SUID permission listing or full LinPEAS findings. Do not manufacture them. The config capture does not show TARGETURI.
- Blue: no selected MS17-010 scan-result capture or subsequent native-shell whoami/priv/hostname output. Existing scan/follow-up text remains explicitly methodological rather than captured output. The configuration capture uses port 4444, not the supplied walkthrough's 2222.
- Butler: no safe selected screenshot for the credential test or original Jenkins shell command. The Burp screenshot was excluded because it exposes login payloads and a session cookie. No selected WinPEAS privileges, exact service payload/trigger chain or 1053 error capture. The existing caveat about unproven escalation attribution remains.
- Browser/reference-page screenshots with unrelated bookmarks and personal context were excluded. Duplicate captures and generated investigation diagrams were excluded.
- Recommended remediation is advice, not a claim of remediation performed or a formal client report.

## Academy draft

Primary source: owner's Obsidian Academy/Reporting.md, cross-checked against its linked lab captures. Butler/Reporting.md was also reviewed; the existing complete Butler article already reflects it and was not duplicated.

Academy selected PNGs preserve original IHDR/IDAT pixel data, stripping ancillary metadata:
- academy-ftp.png — 20261022091244: anonymous login and note retrieval.
- academy-foothold.png — 20261022101923: captured listener uses 1234; www-data identity.
- academy-cron.png — 20261023115310: UID=0 executes backup.sh.
- academy-root.png — 20261023115735: modified script uses 8080 and callback confirms root.

Reporting.md's later example listener ports 4444 and 5555 differ from the captures; the article uses only the captured ports (1234 and 8080) for those stages. Expected Nmap/output examples are not represented as captured evidence. No credential/hash material was copied. Excluded config, note and cracking screenshots carry credentials or hashes; external cheat-sheet capture is not evidence of an executed command. Permission/listing, upload exchange, full LinPEAS output and exact cracking transcript remain evidence gaps. No performed remediation/retest claimed.

## Dev

Primary source: owner's Obsidian Dev/Reporting.md. Cross-checked linked scanning notes plus contemporaneous captures. The report's SSH `user` is explicitly treated as a placeholder; an earlier captured jp attempt failed, whereas later captures show jeanpaul. The exact successful login command is not retained. The report's expected id output is not claimed as observed.

Selected authentic PNGs (original pixel payloads; metadata stripped):
- dev-nfs.png — 20261023123203: export listing.
- dev-archive.png — 20261023123947: archive extraction, filenames only.
- dev-sudo.png — 20261023161749: NOPASSWD /usr/bin/zip for jeanpaul.
- dev-root.png — 20261023162559: actual sudo ZIP invocation, root identity and dev hostname.

Excluded: 20261023124042 exposes an OpenSSH private key; 20261023174827 exposes the recovered archive password. Generated diagrams/flag explanations are not used as terminal evidence. No passwords, credential hashes or private-key contents were copied. Generic user template preserved; root result directly captured. Technique cross-check: https://gtfobins.org/gtfobins/zip/ .

## Target architecture review

Architecture values describe the target guest operating systems, not the Kali attacker or physical host. x86_64, amd64 and Windows x64 are the 64-bit x86 architecture. The owner confirmed that Blackpearl, Butler and Dev were the standard TCM Practical Ethical Hacking VM downloads, without rebuilding their operating systems.

- Blue: x64 (64-bit), directly verified in the retained `blue-system.png` Meterpreter `sysinfo` capture.
- Academy: x86_64 (64-bit), directly verified in the retained `academy-foothold.png` target Linux banner.
- Blackpearl: x86_64 (64-bit), cross-checked against the original researcher's target `sysinfo` transcript naming `blackpearl`: https://emvee-nl.github.io/posts/TCM-Writeup-Black-Pearl/ .
- Butler: x64 (64-bit), cross-checked against the original researcher's `systeminfo` transcript naming `BUTLER` and `System Type: x64-based PC`: https://emvee-nl.github.io/posts/TCM-Writeup-Butler/ .
- Dev: x86_64 (64-bit), cross-checked against the original researcher's target reverse-shell banner, `Linux dev 4.19.0-16-amd64 ... x86_64 GNU/Linux`, in section 12: https://ainkun.medium.com/tcmsecurity-dev-write-up-eee565738e78 .

The external transcripts establish the standard lab images' architecture; they are not represented as captures from the owner's sessions. No new terminal output or screenshots were added.

## sca-triage case study

`site/sca-triage.html` shows terminal output as text rather than screenshots. The four steps come from one run of the commands they show on OWASP NodeGoat at commit `c5cb68a`, using sca-triage 1.2.3 as published on npm (`npx sca-triage`), on a GitHub Actions runner with Node 22.23.4 and npm 10.9.9 (run 42737443859, since deleted with the temporary job; the full log of that step is kept in [`evidence/sca-triage-1.2.3-nodegoat-run.txt`](evidence/sca-triage-1.2.3-nodegoat-run.txt)). The temporary sca-triage branch added only the workflow file; the tool itself came from npm. The same job ran `npm ls --all` on the fixed copy and found no invalid entries. It ran there because this project's cloud environment cannot download the GitHub tarball that one NodeGoat dev dependency (`grunt-if`) installs from. The text is the log of that step with GitHub's timestamps removed. Trimmed: each finding's advisory list, the P2 and P3 findings in both scans and in the report's tables, the report's generation timestamp, and lines that repeat earlier output: 8 of the 9 scoped `semver` overrides in the `fix` output (all 9 are shown in the plan), and in the report 10 of the 12 P1 rows of the "Before" table and 15 of the 17 "Changes applied" (all are shown in the scan and `fix` output). Each cut is marked with "…". Nothing else was edited. The table under "What changed" is built from the plan, fix and rescan output. The counts in the text (437 advisories; 130 development-only, 61 bundled and 10 unfixable among the other 168 findings) come from `npx sca-triage scan NodeGoat --json` with the same package. `npm test` (96 tests) passed on the published commit (`9c963de`, tag `v1.2.3`). The page labels the current release, 1.2.4 (`02c7817`), a documentation-only release: the `bin/` and `src/` files in its npm package are byte-identical to those in 1.2.3's, and its 96 tests pass. The earlier v1.2.2 run reported 13 P1; the 13th, `debug@2.2.0` "via helmet", came from a `require` in a comment (NodeGoat's `server.js` has `helmet` commented out), which 1.2.3 no longer counts. No passwords, tokens, cookies or private keys appear.

## sast-triage case study

`site/sast-triage.html` shows terminal output as text rather than screenshots. The two output blocks (the whole-project scan and the pull request scan) are the output of the commands they show on OWASP NodeGoat at commit `c5cb68a`, using sast-triage v2.1.0 (`5c463aa`) and Semgrep 1.79.0, the version `requirements-cli.txt` pins. Both were re-run on 2026-11-10 in a Linux environment with Python 3.13.18, from a clean checkout of each repository (sast-triage at tag `v2.1.0`, NodeGoat at `c5cb68a`): every line on the page matched, the whole-project scan exited with code 1 and the pull request scan (`--base HEAD~2`, which is `b2aed38`) with code 0. Trimmed from both blocks: the "Skipped: …" line that lists the folders left out, and the closing priority legend. Trimmed from the whole-project block: the seven P1 findings repeated under the gate line, replaced by "… the seven P1 findings above". Nothing else was edited. GitHub Actions passed `make check` on Python 3.11, 3.12, 3.13 and 3.14 and the Action self-test for `5c463aa` (run 42830613996); the 192-test figure is from that run's log (`192 passed` on each Python version).

