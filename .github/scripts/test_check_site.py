#!/usr/bin/env python3
"""Tests for the image metadata check in check_site.py. Standard library only.

Usage: python3 .github/scripts/test_check_site.py

Every image is built here from bytes, so no photo or image tool is needed.
The PNG files decode as real images. The WebP and JPEG files are well-formed
containers with filler where the pixels would be, because the check reads the
container and never decodes pixels.
"""
import contextlib
import io
import pathlib
import struct
import sys
import tempfile
import unittest
import zlib
from unittest import mock

sys.dont_write_bytecode = True  # leave no __pycache__ folder in the repository
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_site  # noqa: E402

NEAR, LATE = 1_000, 70_000  # filler bytes ahead of the metadata; 70,000 is past 64 KiB
TIFF = b"II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # an EXIF block with no tags
XMP = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'/>"
EXIF_FOUND = ["image still has EXIF metadata"]


def png_chunk(kind, data=b""):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(filler, *chunks):
    """A one-row greyscale PNG with `filler` bytes of pixel data, then `chunks`."""
    header = struct.pack(">IIBBBBB", filler - 1, 1, 8, 0, 0, 0, 0)
    pixels = zlib.compress(bytes(filler), 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"sRGB", b"\x00")
            + png_chunk(b"IDAT", pixels) + b"".join(chunks) + png_chunk(b"IEND"))


def webp_chunk(kind, data=b""):
    return kind + struct.pack("<I", len(data)) + data + bytes(len(data) % 2)


def webp(filler, *chunks):
    """A WebP container with `filler` bytes in the image chunk, then `chunks`."""
    body = b"WEBP" + webp_chunk(b"VP8X", bytes(10)) + webp_chunk(b"VP8 ", bytes(filler)) + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def jpeg_segment(marker, data=b""):
    return bytes([0xFF, marker]) + struct.pack(">H", len(data) + 2) + data


def jpeg(filler, *segments):
    """A JPEG container with `filler` bytes of other segments, then `segments`."""
    padding = b"".join(jpeg_segment(0xE2, bytes(min(35_000, filler - done)))
                       for done in range(0, filler, 35_000))
    return b"\xff\xd8" + jpeg_segment(0xE0, b"JFIF\x00") + padding + b"".join(segments) + b"\xff\xd9"


PNG_EXIF = png_chunk(b"eXIf", TIFF)
WEBP_EXIF = webp_chunk(b"EXIF", TIFF)
JPEG_EXIF = jpeg_segment(0xE1, b"Exif\x00\x00" + TIFF)


def check(images):
    """Runs the site check on a site holding `images`.

    Returns the exit code and the problems reported for each file.
    """
    with tempfile.TemporaryDirectory() as site:
        for name, data in images.items():
            pathlib.Path(site, name).write_bytes(data)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["check_site.py", site]), contextlib.redirect_stdout(out):
            code = check_site.main()
    *lines, summary = out.getvalue().splitlines()
    problems = {}
    for line in lines:
        name, _, problem = line.partition(": ")
        problems.setdefault(name, []).append(problem)
    assert summary == f"0 pages checked, {len(lines)} problem(s)", summary
    return code, problems


class ImageMetadataTest(unittest.TestCase):
    def test_exif_is_found_wherever_it_sits_in_the_file(self):
        code, problems = check({
            "control-small.png": png(NEAR, PNG_EXIF),
            "control-small.webp": webp(NEAR, WEBP_EXIF),
            "control-small.jpg": jpeg(NEAR, JPEG_EXIF),
            "late-exif.png": png(LATE, PNG_EXIF),
            "late-exif.webp": webp(LATE, WEBP_EXIF),
            "late-exif.jpg": jpeg(LATE, JPEG_EXIF),
        })
        self.assertEqual(problems, {
            "control-small.png": EXIF_FOUND, "control-small.webp": EXIF_FOUND,
            "control-small.jpg": EXIF_FOUND,
            "late-exif.png": EXIF_FOUND, "late-exif.webp": EXIF_FOUND, "late-exif.jpg": EXIF_FOUND,
        })
        self.assertEqual(code, 1)

    def test_format_is_read_from_the_file_not_its_name(self):
        code, problems = check({"photo.png": jpeg(LATE, JPEG_EXIF), "photo.jpg": webp(LATE, WEBP_EXIF)})
        self.assertEqual(problems, {"photo.png": EXIF_FOUND, "photo.jpg": EXIF_FOUND})
        self.assertEqual(code, 1)

    def test_text_and_xmp_metadata_is_found_wherever_it_sits_in_the_file(self):
        code, problems = check({
            "comment.png": png(LATE, png_chunk(b"tEXt", b"Creation Time\x002026:11:12 06:00:00")),
            "exif-profile.png": png(LATE, png_chunk(
                b"zTXt", b"Raw profile type exif\x00\x00" + zlib.compress(TIFF))),
            "xmp.png": png(LATE, png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + XMP)),
            "xmp.webp": webp(LATE, webp_chunk(b"XMP ", XMP)),
            "xmp.jpeg": jpeg(LATE, jpeg_segment(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + XMP)),
        })
        self.assertEqual(problems, {
            "comment.png": ["image still has text metadata (tEXt chunk)"],
            "exif-profile.png": ["image still has text metadata (zTXt chunk)"],
            "xmp.png": ["image still has text metadata (iTXt chunk)"],
            "xmp.webp": ["image still has XMP metadata"],
            "xmp.jpeg": ["image still has XMP metadata"],
        })
        self.assertEqual(code, 1)

    def test_images_without_metadata_pass(self):
        code, problems = check({
            "small.png": png(NEAR), "small.webp": webp(NEAR), "small.jpg": jpeg(NEAR),
            "large.png": png(LATE), "large.webp": webp(LATE), "large.jpg": jpeg(LATE),
        })
        self.assertEqual(problems, {})
        self.assertEqual(code, 0)

    def test_image_that_cannot_be_read_to_the_end_is_reported(self):
        code, problems = check({
            "cut-short.png": png(LATE, PNG_EXIF)[:66_000],
            "cut-short.webp": webp(LATE, WEBP_EXIF)[:66_000],
            "extra-bytes.png": png(NEAR) + bytes(LATE) + PNG_EXIF,
            "not-an-image.png": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        })
        self.assertEqual(sorted(problems),
                         ["cut-short.png", "cut-short.webp", "extra-bytes.png", "not-an-image.png"])
        for name, found in problems.items():
            self.assertEqual(len(found), 1, name)
            self.assertIn("image cannot be checked for metadata: ", found[0], name)
        self.assertEqual(code, 1)

    def test_image_over_the_size_limit_is_reported_not_skipped(self):
        images = {"big.png": png(LATE), "big.webp": webp(LATE), "big.jpg": jpeg(LATE)}
        with mock.patch.object(check_site, "MAX_IMAGE_BYTES", 65_536):
            code, problems = check(images)
        self.assertEqual(sorted(problems), ["big.jpg", "big.png", "big.webp"])
        for name, found in problems.items():
            self.assertEqual(
                found, ["image is larger than 65536 bytes, too large to check for metadata"], name)
        self.assertEqual(code, 1)


class CredentialValueTest(unittest.TestCase):
    """A credential value shown on a page fails; placeholders and descriptions pass (A-422)."""

    # Synthetic stand-ins only. None of these is, or resembles, a real password.
    SHOWN = {
        # Butler-shaped pairs, 'password: X' forms and tool output
        "butler pair in two code elements": "<p><code>jenkins</code> / <code>Zq7stand1n</code> logged me in</p>",
        "pair inside one code element": "<p><code>admin / Zq7stand1n</code></p>",
        "password colon": "<p>password: Zq7stand1n</p>",
        "password equals in a pre block": "<pre><code>mysql --user=a\npass=Zq7stand1n</code></pre>",
        "password is in code": "<p>The password is <code>Zq7stand1n</code>.</p>",
        "password is in quotes": "<p>The password was \u201c'Zq7stand1n'\u201d.</p>",
        "passphrase": "<p>Passphrase: Zq7stand1n</p>",
        "api key": "<p>API key: Zq7stand1n</p>",
        "token": "<code>token=Zq7stand1n</code>",
        "table row with a password cell": "<table><tr><th>Password</th><td>Zq7stand1n</td></tr></table>",
        # user:pass URLs and user:pass pairs
        "ssh URL with user:pass": "<p><code>ssh://admin:Zq7stand1n@10.0.0.5</code></p>",
        "http URL in prose": "<p>Opened http://admin:Zq7stand1n@&lt;TARGET_IP&gt;:8080/ next.</p>",
        "bare user:pass@host": "<code>ftp admin:Zq7stand1n@10.0.0.5</code>",
        "mysql URL in pre": "<pre><code>mysql://root:Zq7stand1n@localhost/db</code></pre>",
        "user:password pair": "<p>Tried <code>admin:Zq7stand1n</code> over SSH</p>",
        "curl -u": "<pre><code>curl -u admin:Zq7stand1n http://&lt;TARGET_IP&gt;/</code></pre>",
        "curl --user": "<pre><code>curl --user admin:Zq7stand1n http://&lt;TARGET_IP&gt;/</code></pre>",
        "smbclient -U user%pass": "<pre><code>smbclient -U 'admin%Zq7stand1n' //&lt;TARGET_IP&gt;/share</code></pre>",
        # creds and pairs in prose and code
        "creds colon pair": "<p>creds: admin/Zq7stand1n</p>",
        "default creds in code": "<p>The default creds are <code>admin/Zq7stand1n</code>.</p>",
        "logged in as pair": "<p>Logged in as admin / Zq7stand1n</p>",
        "valid credentials line": "<p>Valid credentials: admin:Zq7stand1n</p>",
        "login colon pair": "<p>login: root/Zq7stand1n</p>",
        # tool output
        "hydra success line": "<pre><code>[22][ssh] host: 10.0.0.5   login: admin   password: Zq7stand1n</code></pre>",
        "hydra login password line": "<pre><code>login: admin password: Zq7stand1n</code></pre>",
        "hydra SUCCESS line": "<pre><code>[SUCCESS] - 10.0.0.5:445 - Login Successful: admin:Zq7stand1n</code></pre>",
        "netexec plus line": "<pre><code>SMB 10.0.0.5 445 DC01 [+] corp.local\\admin:Zq7stand1n (Pwn3d!)</code></pre>",
        "valid credentials in a pre block": "<pre><code>[+] Valid credentials: admin:Zq7stand1n</code></pre>",
        "intruder row in a pre block": "<pre><code>Request Payload1 Payload2 Status Length\n142 admin Zq7stand1n 200 181</code></pre>",
        "intruder row in a table": "<table><tr><td>142</td><td>admin</td><td>Zq7stand1n</td><td>200</td><td>181</td></tr></table>",
        # command flags
        "hydra -p": "<pre><code>hydra -l admin -p Zq7stand1n ssh://&lt;TARGET_IP&gt;</code></pre>",
        "sshpass -p": "<pre><code>sshpass -p Zq7stand1n ssh admin@&lt;TARGET_IP&gt;</code></pre>",
        "sshpass -p quoted": "<pre><code>sshpass -p 'Zq7stand1n' ssh admin@&lt;TARGET_IP&gt;</code></pre>",
        "mysql -pVALUE": "<pre><code>mysql -u root -pZq7stand1n</code></pre>",
        "--password flag": "<pre><code>tool --user admin --password Zq7stand1n</code></pre>",
        "--password=": "<pre><code>tool --password=Zq7stand1n</code></pre>",
        "evil-winrm -p": "<pre><code>evil-winrm -i &lt;TARGET_IP&gt; -u admin -p Zq7stand1n</code></pre>",
        "netexec -p": "<pre><code>netexec smb &lt;TARGET_IP&gt; -u admin -p Zq7stand1n</code></pre>",
        # attributes
        "pair in an image alt": '<img src="a.png" alt="Login with admin / Zq7stand1n" width="1" height="1">',
        "creds in an image alt": '<img src="a.png" alt="creds: admin/Zq7stand1n" width="1" height="1">',
        "secret in a title": '<a href="/" title="secret=Zq7stand1n">x</a>',
        "URL in a title": '<a href="/" title="ssh://admin:Zq7stand1n@10.0.0.5">x</a>',
        "hydra line in aria-label": '<div aria-label="login: admin password: Zq7stand1n">x</div>',
        "pwd in figure alt": '<img src="a.png" alt="pwd = Zq7stand1n" width="1" height="1">',
    }
    FINE = {
        # placeholders
        "password placeholder": "<p>password: &lt;PASSWORD&gt;</p>",
        "pair with placeholder": "<p><code>jenkins</code> / <code>&lt;PASSWORD&gt;</code></p>",
        "any upper-case placeholder": "<p>token=&lt;API_TOKEN&gt; secret: &lt;SECRET_VALUE_2&gt;</p>",
        "lower-case angle placeholder": "<p>password: &lt;password&gt;</p>",
        "stars": "<p>password: *****</p>",
        "bullets": "<p>password: \u2022\u2022\u2022\u2022\u2022\u2022</p>",
        "shell variable": "<pre><code>sshpass -p $PASSWORD ssh admin@&lt;TARGET_IP&gt;</code></pre>",
        "workflow secret": "<pre><code>token: ${{ secrets.GITHUB_TOKEN }}</code></pre>",
        "URL with placeholder": "<code>ssh://admin:&lt;PASSWORD&gt;@10.0.0.5</code>",
        "URL with stars": "<code>ssh://admin:*****@10.0.0.5</code>",
        "smbclient placeholder": "<pre><code>smbclient -U 'admin%&lt;PASSWORD&gt;' //host/share</code></pre>",
        "creds placeholder pair": "<p>creds: admin/&lt;PASSWORD&gt;</p>",
        "generic user/pass": "<p>creds: user/pass</p>",
        "hydra placeholder": "<pre><code>hydra -l admin -p &lt;PASSWORD&gt; ssh://&lt;TARGET_IP&gt;</code></pre>",
        # flags that are not secrets
        "hydra wordlist -P": "<pre><code>hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://&lt;TARGET_IP&gt;</code></pre>",
        "nmap ports": "<pre><code>nmap -sS -p 22,80,8080 &lt;TARGET_IP&gt;</code></pre>",
        "mkdir -p": "<pre><code>mkdir -p ./evidence</code></pre>",
        "fcrackzip -p wordlist": "<pre><code>fcrackzip -v -u -D -p /usr/share/wordlists/rockyou.txt x.zip</code></pre>",
        "mysql prompts for the password": "<pre><code>mysql -u root -p mydb</code></pre>",
        "ssh port": "<pre><code>ssh -p 2222 admin@&lt;TARGET_IP&gt;</code></pre>",
        "msfvenom payload": "<pre><code>msfvenom -p windows/x64/shell_reverse_tcp LHOST=&lt;IP&gt;</code></pre>",
        "metasploit payload": "<pre><code>set PAYLOAD windows/x64/meterpreter/reverse_tcp</code></pre>",
        "password-stdin": "<pre><code>docker login --password-stdin</code></pre>",
        # descriptions of passwords and tool output without a credential
        "password list": "<p>I tried a short password list.</p>",
        "password hash": "<p>The password hash was cracked offline.</p>",
        "password spraying": "<p>Password spraying: one password tried across many accounts.</p>",
        "cracked the password": "<p>A wordlist cracked the password in a second.</p>",
        "password reused": "<p>The password was reused across services.</p>",
        "descriptive is": "<p>The password is reused across services.</p>",
        "passwords omitted": "<p>Tested passwords are omitted: hashes and keys too.</p>",
        "last login line": "<pre><code>Last login: Tue Nov 25 on ttys000</code></pre>",
        "last login in prose": "<p>Last login: Tue</p>",
        "pass then a word": "<p>Run offline with npm test and pass: version matching works.</p>",
        "token then a word": "<p>sast-triage itself uses no token: unlike the app it needs none.</p>",
        "token needs a scope": "<p>token: read-only access</p>",
        "ssh prompt": "<pre><code>jp@&lt;TARGET_IP&gt;'s password:\nPermission denied</code></pre>",
        "etc passwd": "<p>Read <code>/etc/passwd</code> and the NOPASSWD rule.</p>",
        "windows path": "<p>Looked in <code>C:\\Users\\Public</code>.</p>",
        "host and port": "<p><code>localhost:8080</code> and <code>/etc/passwd</code></p>",
        "mailto text": "<p>Write to <code>mailto:me@example.com</code>.</p>",
        "email next to a colon": "<p>Contact: me@example.com</p>",
        "label then word": "<p>Login: required</p>",
        "slash pair of numbers": "<p><code>3</code> / <code>4</code> checks</p>",
        "valid input and output": "<p>Valid input/output pairs are listed below.</p>",
        "version in a table": "<table><tr><td>3</td><td>sast-triage</td><td>v1.2</td><td>200</td><td>5</td></tr></table>",
        "table password cell with a word": "<table><tr><th>Password</th><td>hashed</td></tr></table>",
        "script text": "<script>var password = 'Zq7stand1n';</script>",
        "token in prose": "<p>CI tokens are read-only.</p>",
    }

    def test_shown_credential_values_fail_and_the_value_is_never_printed(self):
        for name, html in self.SHOWN.items():
            with self.subTest(name):
                found = check_site.credential_problems(html)
                self.assertEqual(len(found), 1, found)
                self.assertIn("shows a credential value (Z... (10 characters))", found[0])
                self.assertNotIn("Zq7stand1n", found[0])

    def test_placeholders_and_descriptions_pass(self):
        for name, html in self.FINE.items():
            with self.subTest(name):
                self.assertEqual(check_site.credential_problems(html), [])

    def test_a_default_login_word_counts_in_prose_and_code(self):
        for html in ("<p>creds: admin/admin</p>", "<p>password: admin</p>", "<code>--password root</code>"):
            with self.subTest(html):
                self.assertEqual(len(check_site.credential_problems(html)), 1, html)

    def test_report_names_the_line(self):
        html = "<p>ok</p>\n<p>fine</p>\n<p>password: Zq7stand1n</p>"
        self.assertEqual(check_site.credential_problems(html)[0][:7], "line 3:")

    def test_no_page_under_site_shows_a_credential_value(self):
        site = pathlib.Path(__file__).resolve().parents[2] / "site"
        pages = sorted(site.rglob("*.html"))
        self.assertEqual(len(pages), 12)
        for page in pages:
            with self.subTest(page=str(page.relative_to(site))):
                self.assertEqual(check_site.credential_problems(page.read_text(encoding="utf-8")), [])

    def test_main_fails_a_site_that_shows_a_credential_value(self):
        with tempfile.TemporaryDirectory() as site:
            pathlib.Path(site, "index.html").write_text(
                "<!doctype html><html lang=en><title>t</title><p>password: Zq7stand1n</p></html>")
            out = io.StringIO()
            with mock.patch.object(sys, "argv", ["check_site.py", site]), contextlib.redirect_stdout(out):
                code = check_site.main()
        self.assertEqual(code, 1)
        self.assertIn("index.html: line 1: shows a credential value (Z... (10 characters))", out.getvalue())
        self.assertNotIn("Zq7stand1n", out.getvalue())


class ResumeAccentTest(unittest.TestCase):
    def test_accented_resume_is_reported_in_any_case(self):
        for word in ("R\u00e9sum\u00e9", "r\u00e9sum\u00e9", "R\u00c9SUM\u00c9"):
            with self.subTest(word=word):
                self.assertEqual(check_site.accent_problems(f"<p>ok</p>\n<a>{word}</a>"),
                                 ["line 2: write 'Resume' without accents"])

    def test_plain_resume_passes(self):
        self.assertEqual(check_site.accent_problems("<a>Resume</a> <a>resume</a>"), [])

    def test_no_page_under_site_has_accented_resume(self):
        site = pathlib.Path(__file__).resolve().parents[2] / "site"
        for page in sorted(site.rglob("*.html")):
            with self.subTest(page=str(page.relative_to(site))):
                self.assertEqual(check_site.accent_problems(page.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
