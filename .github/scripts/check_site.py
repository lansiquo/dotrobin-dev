#!/usr/bin/env python3
"""Checks the static site before it deploys. Standard library only.

Usage: python3 .github/scripts/check_site.py [site_dir]

Fails (exit 1) on: unbalanced HTML, a missing <title> or <html lang>,
duplicate ids, internal links or assets that do not exist, links to
#anchors that do not exist, images without alt text or width/height,
sitemap entries without a page, a credential value shown next to a
credential word (see credential_problems), and PNG, WebP or JPEG images that still
carry EXIF, XMP or PNG text metadata, or that cannot be read in full to
check. External links are not fetched.
"""
import bisect
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
# Elements whose end tag HTML lets you leave out.
OPTIONAL_END = {"p", "li", "dt", "dd", "tr", "td", "th", "thead", "tbody",
                "tfoot", "option", "colgroup", "caption", "rt", "rp", "optgroup"}
SITE_HOST = "dotrobin.dev"
# An image larger than this is reported, not read: a file that was not read
# in full cannot be shown to be free of metadata.
MAX_IMAGE_BYTES = 32 * 1024 * 1024
PNG_METADATA = {b"eXIf": "EXIF metadata",
                b"tEXt": "text metadata (tEXt chunk)",
                b"zTXt": "text metadata (zTXt chunk)",
                b"iTXt": "text metadata (iTXt chunk)"}
WEBP_METADATA = {b"EXIF": "EXIF metadata", b"XMP ": "XMP metadata"}
JPEG_METADATA = {b"Exif\x00\x00": "EXIF metadata",
                 b"http://ns.adobe.com/xap/1.0/\x00": "XMP metadata"}


# Credential values shown on a page (A-422). Code text is wrapped in CODE_ON
# and CODE_OFF so the rules can tell a code element from prose; table cells are
# joined by a tab so a row reads as one line.
CODE_ON, CODE_OFF, MARKS = "\x01", "\x02", "\x01\x02"
SHOWN_ATTRS = ("alt", "title", "aria-label")
INLINE = {"a", "abbr", "b", "code", "em", "i", "kbd", "mark", "small", "span", "strong", "sub", "sup"}
CELLS = {"td", "th"}
SECRET = r"(?:password|passwd|pass|pwd|passphrase|secret|token|api[ _-]?key)s?"
# Words that point at a credential pair: 'creds: admin/X', 'logged in as admin / X', 'accepted admin:X'.
CUE = (r"(?:creds?|credentials?|logins?|log(?:ged)?[ \t]+in|sign(?:ed)?[ \t]+in|accepted|authenticat\w*|valid"
       r"|default|worked|success\w*|cracked|found|\[\+\])")
VALUE = rf"{CODE_ON}?[\"'`]?([^\s{MARKS}\"'`,;]+)"
USER = rf"{CODE_ON}?[\"'`]?(?:[\w.-]+\\)?(?!(?:valid|creds?|credentials?|logins?|success\w*)\b)([A-Za-z][\w.-]*)"
NOT_A_VALUE = {"the", "a", "an", "and", "or", "to", "of", "in", "none", "n/a", "required", "not", "no", "set",
               "empty", "blank", "hidden", "redacted", "removed", "true", "false", "null", "string", "str",
               "int", "bool", "undefined", "user", "username", "pass", "password", "passwd", "pwd", "secret",
               "token", "key", "value", "x", "xx", "xxx"}
MAIL = r"(?!(?:mailto|email|e-mail|contact|from|to|cc):)"
# Plain words that still count as a credential where prose would otherwise hide them.
DEFAULTS = {"admin", "administrator", "root", "toor", "password", "passw0rd", "guest", "test", "default",
            "changeme", "letmein", "welcome", "qwerty", "hunter2", "secret", "user", "pass"}
PLACEHOLDER = re.compile(r"<[^<>]+>|\*+|\u2022+|\.{3}|\u2026|x{3,}|\$.*|\{\{.*|%s|\[?REDACTED\]?|[A-Z][A-Z_]+")
VERSION = re.compile(r"v?\d+(?:\.\d+)+")
# Each rule is (pattern, when the value must look like a credential): 'always',
# 'prose' (outside code) or 'never'. The value is the pattern's last group.
RULES = (
    # 'password: X', 'pass=X', 'login: Y password: Z' (hydra), 'token=X'
    (re.compile(rf"\b{SECRET}[ \t]*[:=][ \t]*{VALUE}", re.I), "prose"),
    # 'password is X': prose follows these words, so the value must be in code or quotes.
    (re.compile(rf"\b{SECRET}\s+(?:is|was)\s+(?:{CODE_ON}|[\"'`\u2018\u201c])+([^\s{MARKS}\"'`\u2019\u201d]+)", re.I), "always"),
    # a table row 'Password | X'
    (re.compile(rf"(?:^|\t){CODE_ON}?[ \t]*{SECRET}[ \t]*\t+[ \t]*{CODE_ON}?([^\s{MARKS}]+)", re.I | re.M), "always"),
    # 'user / X' in code, split across two code elements or inside one.
    (re.compile(rf"{CODE_ON}([A-Za-z][\w.-]*){CODE_OFF}\s+/\s+{CODE_ON}([^\s{MARKS}]+){CODE_OFF}"
                rf"|{CODE_ON}(?:[^{CODE_OFF}]*?\s)?([A-Za-z][\w.-]*) / ([^\s\-/{MARKS}][^\s{MARKS}]*)"), "never"),
    # 'creds: admin/X', 'logged in as admin / X', 'Valid credentials: admin:X', '[+] corp\admin:X'
    (re.compile(rf"(?<!\w){CUE}(?!\w)(?:[ \t]+(?:with|as|is|are|was|using|me|in|on|to|for))*[ \t]*[:=]?[ \t]*{USER}[ \t]*[/:][ \t]*{VALUE}", re.I), "prose"),
    # 'user:X' as a whole code element, or after -u / --user / --userpass.
    (re.compile(rf"{CODE_ON}{MAIL}([A-Za-z][\w.-]+):(?!\d+{CODE_OFF})([^\s:/\\<>{MARKS}]+){CODE_OFF}"
                rf"|(?:\s-u|--user(?:pass)?)[ =]{CODE_ON}?[\"']?[\w.-]+:([^\s:/<>{MARKS}\"']+)"), "never"),
    # 'user:X@host' in a URL or a login string, and '-U user%X'
    (re.compile(rf"(?<![\w-]){MAIL}[A-Za-z][\w.-]*:([^\s:/@<>{MARKS}]+)@[\w<$]"), "never"),
    (re.compile(rf"(?:\s-U|--user(?:name)?)[ =]{CODE_ON}?[\"']?[\w.-]+%([^\s{MARKS}\"']+)"), "never"),
    # a Burp Intruder row 'request  user  X  status  length'
    (re.compile(rf"^[ \t]*{CODE_ON}?\d+[ \t]+[A-Za-z][\w.@-]*[ \t]+([^\s\t{MARKS}]+)[ \t]+[23]\d\d[ \t]+\d+[ \t]*{CODE_OFF}?$", re.M), "prose"),
)
# Command flags that carry a secret, on a line that runs a tool known to take one.
# '-P' is a wordlist and never counts; 'mysql -p db' prompts, so mysql needs '-pX'.
SPACED_TOOLS = re.compile(r"\b(?:hydra|medusa|sshpass|evil-winrm|crackmapexec|netexec|nxc|cme|smbmap|mongosh?|xfreerdp)\b")
ATTACHED_TOOLS = re.compile(r"\b(?:mysql|mysqldump|mysqladmin|mariadb)\b")
FLAG_VALUE = rf"{CODE_ON}?[\"'`]?([^\s\-{MARKS}\"'`;|&][^\s{MARKS}\"'`;|&]*)"
LONG_FLAG = re.compile(rf"(?<![\w-])--(?:password|passwd|pass|pwd|passphrase)(?![\w-])[ =]+{FLAG_VALUE}")
SPACED_FLAG = re.compile(rf"(?<![\w-])-p[ \t]+{FLAG_VALUE}|(?<![\w/-])/p:{FLAG_VALUE}")
ATTACHED_FLAG = re.compile(rf"(?<![\w-])-p(?![\s=-]){FLAG_VALUE}")


class TextCollector(HTMLParser):
    """The text a visitor can read or hear: text nodes plus alt, title and aria-label."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.starts, self.size, self.hidden, self.code = [], [], 0, 0, 0

    def add(self, text):
        self.starts.append((self.size, self.getpos()[0]))
        self.parts.append(text)
        self.size += len(text)

    def boundary(self, tag):
        if tag in CELLS:
            self.add("\t")
        elif tag not in INLINE:
            self.add("\n")  # a block boundary separates words, so 'title' and 'p' text never join

    def handle_starttag(self, tag, attrs):
        self.boundary(tag)
        if tag in ("script", "style"):
            self.hidden += 1
        for name, value in attrs:
            if name in SHOWN_ATTRS and value:
                self.add(f" {CODE_ON}{value}{CODE_OFF} ")
        if tag in ("code", "pre"):
            self.code += 1
            if self.code == 1:
                self.add(CODE_ON)

    def handle_endtag(self, tag):
        self.boundary(tag)
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        if tag in ("code", "pre") and self.code:
            self.code -= 1
            if not self.code:
                self.add(CODE_OFF)

    def handle_data(self, data):
        if not self.hidden:
            self.add(data)

    def line_at(self, offset):
        return self.starts[bisect.bisect_right([s for s, _ in self.starts], offset) - 1][1]


def mask(value):
    """First character and length only; the value itself is never printed."""
    return f"{value[0]}... ({len(value)} characters)"


def looks_like_credential(value):
    """True for a default login word or a value with a digit and a letter, or a symbol; false for plain words."""
    v = value.lower()
    if v in DEFAULTS:
        return True
    if VERSION.fullmatch(v):
        return False
    return bool(re.search(r"[a-z]", v) and re.search(r"\d", v) or re.search(r"[!@#$%^&*+=~?]", v))


def is_credential_value(value, strict):
    value = value.rstrip(".")
    if not value or PLACEHOLDER.fullmatch(value) or value.lower() in NOT_A_VALUE:
        return False
    if value.isdigit():
        return not strict and len(value) >= 4  # prose numbers are counts and years; code may hold '123456'
    return looks_like_credential(value) if strict else True


def flag_matches(text):
    """Secrets passed as command-line flags, found line by line."""
    offset = 0
    for line in text.split("\n"):
        patterns = [LONG_FLAG]
        if SPACED_TOOLS.search(line):
            patterns.append(SPACED_FLAG)
        if ATTACHED_TOOLS.search(line):
            patterns.append(ATTACHED_FLAG)
        for pattern in patterns:
            for m in pattern.finditer(line):
                yield offset + m.start(), [g for g in m.groups() if g][-1]
        offset += len(line) + 1


def rule_matches(text):
    spans = [(m.start(), m.end()) for m in re.finditer(f"{CODE_ON}[^{CODE_OFF}]*{CODE_OFF}", text)]
    starts = [s for s, _ in spans]

    def in_code(pos):
        i = bisect.bisect_right(starts, pos) - 1
        return i >= 0 and pos < spans[i][1]

    for pattern, demand in RULES:
        for m in pattern.finditer(text):
            value = [g for g in m.groups() if g][-1]
            yield m.start(), value, demand == "always" or (demand == "prose" and not in_code(m.start()))
    for pos, value in flag_matches(text):
        yield pos, value, False


def credential_problems(html):
    """Lines that show a credential value, masked.

    What it catches: 'password: X' and similar, 'password is X' in code or quotes,
    'user / X' and 'creds: user/X' pairs, 'user:X' after -u or in a whole code
    element, 'user:X@host', hydra and Intruder result lines, '-p X' after hydra,
    sshpass and similar, '--password X', 'mysql -pX', and the same in alt, title
    and aria-label. Placeholders such as <PASSWORD> and ***** pass, as do phrases
    that describe a password without showing one ('password list', 'password hash').
    Outside code, a plain word after 'password:' passes unless it is a common
    default such as 'admin'.
    """
    page = TextCollector()
    page.feed(html)
    page.close()
    text = "".join(page.parts)
    found = {(page.line_at(pos), mask(value.rstrip(".")))
             for pos, value, strict in rule_matches(text) if is_credential_value(value, strict)}
    return [f"line {n}: shows a credential value ({masked}); use a placeholder such as <PASSWORD>"
            for n, masked in sorted(found)]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.refs = [], [], {}, []
        self.has_title = self.has_lang = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if tag == "html" and a.get("lang"):
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        if "id" in a:
            if a["id"] in self.ids:
                self.errors.append(f"line {line}: duplicate id '{a['id']}' (first on line {self.ids[a['id']]})")
            else:
                self.ids[a["id"]] = line
        for attr in ("href", "src", "poster"):
            if a.get(attr):
                self.refs.append((line, a[attr]))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                if part.strip():
                    self.refs.append((line, part.strip().split()[0]))
        if tag == "img":
            if "alt" not in a:
                self.errors.append(f"line {line}: <img> without alt")
            if not (a.get("width") and a.get("height")):
                self.errors.append(f"line {line}: <img> without width and height")
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        line = self.getpos()[0]
        while self.stack and self.stack[-1][0] != tag and self.stack[-1][0] in OPTIONAL_END:
            self.stack.pop()
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            open_tag = self.stack[-1] if self.stack else None
            self.errors.append(f"line {line}: </{tag}> does not match open "
                               + (f"<{open_tag[0]}> from line {open_tag[1]}" if open_tag else "nothing"))

    def finish(self):
        for tag, line in self.stack:
            if tag not in OPTIONAL_END:
                self.errors.append(f"line {line}: <{tag}> is never closed")


def image_problems(path):
    """Lists what is wrong with an image's metadata; empty if nothing is.

    The whole file is read, so metadata is found wherever it sits. PNG and
    WebP files are walked chunk by chunk to the last byte, and JPEG files are
    searched from end to end for the EXIF and XMP markers. The format comes
    from the file's first bytes, not its name. A file that cannot be read to
    the end this way is reported too, because the bytes left unread could
    hold metadata.
    """
    with path.open("rb") as f:
        data = f.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        return [f"image is larger than {MAX_IMAGE_BYTES} bytes, too large to check for metadata"]
    found, unread = [], None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        pos = 8
        while pos < len(data):
            # A chunk is a 4-byte length, a 4-letter type, the data and a 4-byte checksum.
            length, kind = int.from_bytes(data[pos:pos + 4], "big"), data[pos + 4:pos + 8]
            if not kind.isalpha() or pos + 12 + length > len(data):
                unread = f"the PNG data at byte {pos} is not a complete chunk"
                break
            found.append(PNG_METADATA.get(kind))
            pos += 12 + length
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        pos = 12
        while pos < len(data):
            # A chunk is a 4-byte type, a 4-byte length and the data, padded to an even length.
            kind, length = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
            if pos + 8 + length > len(data):
                unread = f"the WebP data at byte {pos} is not a complete chunk"
                break
            found.append(WEBP_METADATA.get(kind))
            pos += 8 + length + length % 2
    elif data.startswith(b"\xff\xd8"):
        found = [name for marker, name in JPEG_METADATA.items() if marker in data]
    else:
        unread = "it is not a PNG, WebP or JPEG file"
    problems = [f"image still has {name}" for name in dict.fromkeys(found) if name]
    if unread:
        problems.append(f"image cannot be checked for metadata: {unread}")
    return problems


def accent_problems(text):
    """Lines that spell Resume with accents; AGENTS.md says to write it without."""
    return [f"line {n}: write 'Resume' without accents"
            for n, line in enumerate(text.splitlines(), 1) if "résumé" in line.lower()]


def text_problems(text):
    """Problems found in a page's text: accented Resume and shown credential values."""
    return accent_problems(text) + credential_problems(text)


def main():
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    problems = []
    pages = {}
    for f in sorted(site.rglob("*.html")):
        p = Page()
        text = f.read_text(encoding="utf-8")
        p.feed(text)
        p.close()
        p.finish()
        if not p.has_title:
            p.errors.append("no <title>")
        if not p.has_lang:
            p.errors.append("no <html lang>")
        p.errors += text_problems(text)
        pages[f] = p

    for f, p in pages.items():
        rel = f.relative_to(site)
        problems += [f"{rel}: {e}" for e in p.errors]
        for line, ref in p.refs:
            u = urlsplit(ref)
            if u.scheme in ("mailto", "tel", "data", "javascript"):
                continue
            if u.scheme or u.netloc:
                if u.netloc != SITE_HOST:
                    continue  # external link: not fetched
                path = u.path
            else:
                path = u.path
            if not path:
                target = f
            elif path.startswith("/"):
                target = site / unquote(path.lstrip("/"))
            else:
                target = (f.parent / unquote(path)).resolve()
            if target.is_dir() or str(path).endswith("/"):
                target = target / "index.html"
            if not target.exists() and target.suffix == "" and target.with_suffix(".html").exists():
                target = target.with_suffix(".html")
            if site not in target.parents and target != site:
                problems.append(f"{rel}: line {line}: '{ref}' points outside the site")
                continue
            if not target.exists():
                problems.append(f"{rel}: line {line}: '{ref}' does not exist")
                continue
            if u.fragment and target.suffix == ".html":
                tp = pages.get(target)
                if tp is not None and unquote(u.fragment) not in tp.ids and u.fragment != "top":
                    problems.append(f"{rel}: line {line}: '{ref}' has no id '{u.fragment}'")

    sitemap = site / "sitemap.xml"
    if sitemap.exists():
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in ET.parse(sitemap).getroot().findall("s:url/s:loc", ns):
            path = urlsplit(loc.text.strip()).path.lstrip("/") or "index.html"
            if not (site / path).exists():
                problems.append(f"sitemap.xml: {loc.text.strip()} has no page")

    for img in sorted(site.rglob("*")):
        if img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            problems += [f"{img.relative_to(site)}: {problem}" for problem in image_problems(img)]

    for line in problems:
        print(line)
    print(f"{len(pages)} pages checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
