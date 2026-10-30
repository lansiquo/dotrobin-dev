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
