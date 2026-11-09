# Write-up evidence

`site/evidence/` holds 23 screenshots: the 12 Blackpearl, Blue and Butler captures in the table below, 4 Academy and 4 Dev captures listed in their sections, and 3 sca-triage captures listed under "sca-triage case study". The 12 tabled screenshots are authentic selected crops from the isolated offline lab. The owner explicitly authorized public disclosure of ordinary lab IPs, usernames, hostnames and system details. The selected unmasked copies were visually inspected before restoration; no passwords, tokens, cookies or private keys were visible in this set. PNG metadata is stripped. Source originals remain outside this repository. No generated terminal imagery is used. The Blue options capture retains its application-chrome crop.

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

`site/sca-triage.html` shows terminal output as text rather than screenshots. The output comes from one local run of the lab commands, supplied by the owner. It is split into four steps; the `git clone` progress lines, a `rm -rf` cleanup command and the report's generation timestamp were trimmed. Paths are limited to `/tmp/lab-copy` and `/tmp/lab-evidence`; no passwords, tokens, cookies or private keys appear.
