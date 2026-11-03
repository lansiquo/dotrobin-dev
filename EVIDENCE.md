# Write-up evidence

All 12 listed screenshots are authentic selected crops from the isolated offline lab. On October 30, 2026, the owner explicitly authorized public disclosure of ordinary lab IPs, usernames, hostnames and system details. The selected unmasked copies were visually inspected before restoration; no passwords, tokens, cookies or private keys were visible in this set. PNG metadata is stripped. Source originals remain outside this repository. No generated terminal imagery is used. The Blue options capture retains its application-chrome crop.

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

## Academy draft (source reviewed November 3, 2026)

Primary source: owner's Obsidian Academy/Reporting.md, cross-checked against its linked lab captures. Butler/Reporting.md was also reviewed; the existing complete Butler article already reflects it and was not duplicated.

Academy selected PNGs preserve original IHDR/IDAT pixel data, stripping ancillary metadata:
- academy-ftp.png — 20261022091244: anonymous login and note retrieval.
- academy-foothold.png — 20261022101923: captured listener uses 1234; www-data identity.
- academy-cron.png — 20261023115310: UID=0 executes backup.sh.
- academy-root.png — 20261023115735: modified script uses 8080 and callback confirms root.

Reporting.md's later example listener ports 4444 and 5555 differ from the captures; article explicitly distinguishes them and uses captured commands for those stages. Expected Nmap/output examples are not represented as captured evidence. No credential/hash material was copied. Excluded config, note and cracking screenshots carry credentials or hashes; external cheat-sheet capture is not evidence of an executed command. Permission/listing, upload exchange, full LinPEAS output and exact cracking transcript remain evidence gaps. No performed remediation/retest claimed.

## Dev (source reviewed November 3, 2026)

Primary source: owner's Obsidian Dev/Reporting.md. Cross-checked linked scanning notes plus contemporaneous captures. The report's SSH `user` is explicitly treated as a placeholder; an earlier captured jp attempt failed, whereas later captures show jeanpaul. The exact successful login command is not retained. The report's expected id output is not claimed as observed.

Selected authentic PNGs (original pixel payloads; metadata stripped):
- dev-nfs.png — 20261023123203: export listing.
- dev-archive.png — 20261023123947: archive extraction, filenames only.
- dev-sudo.png — 20261023161749: NOPASSWD /usr/bin/zip for jeanpaul.
- dev-root.png — 20261023162559: actual sudo ZIP invocation, root identity and dev hostname.

Excluded: 20261023124042 exposes an OpenSSH private key; 20261023174827 exposes the recovered archive password. Generated diagrams/flag explanations are not used as terminal evidence. No passwords, credential hashes or private-key contents were copied. Generic user template preserved; root result directly captured. Technique cross-check: https://gtfobins.org/gtfobins/zip/ .
