#!/usr/bin/env python3
"""Checks the static site before it deploys. Standard library only.

Usage: python3 .github/scripts/check_site.py [site_dir]

Fails (exit 1) on: unbalanced HTML, a missing <title> or <html lang>,
duplicate ids, internal links or assets that do not exist, links to
#anchors that do not exist, images without alt text or width/height,
sitemap entries without a page, and PNG, WebP or JPEG images that still
carry EXIF, XMP or PNG text metadata, or that cannot be read in full to
check. External links are not fetched.
"""
import pathlib
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


def main():
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    problems = []
    pages = {}
    for f in sorted(site.rglob("*.html")):
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        p.close()
        p.finish()
        if not p.has_title:
            p.errors.append("no <title>")
        if not p.has_lang:
            p.errors.append("no <html lang>")
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
