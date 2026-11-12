#!/usr/bin/env python3
"""Fills the version labels before the site deploys. Standard library only.

Usage: python3 .github/scripts/build_versions.py [site_dir]

A page marks each place that shows a tool's current version with two
attributes, the tool and how much of the version is shown:

    <span data-release="sca-triage" data-release-format="X.Y.Z">Version 1.2.4</span>
    <strong data-release="sast-triage" data-release-format="X.Y">Version 2.5</strong>

For every marked element in the HTML pages of <site_dir>, this script replaces
the version number in the element's text with the current one. Nothing else
in a page changes: not the other words in the element, not its attributes and
not any text outside a marked element, so a sentence that says which version
something was checked on stays as it was written.

The current version of each tool:

    sast-triage  the highest version in <site_dir>/data/pulse.json, which
                 build_pulse.py rebuilds just before from the GitHub releases
                 that are not drafts or prereleases and are tagged vX.Y.Z
    sca-triage   dist-tags.latest in the npm registry, the version that
                 `npx sca-triage` runs

Each one must be exactly X.Y.Z: three numbers, without leading zeros. The npm
request carries no token.

A deploy must never break and never show a lower version than the committed
page. So a label keeps its committed text when its tool's version cannot be
read (the registry cannot be reached, an HTTP error, the rate limit, an answer
or a pulse file that is not the expected data), when that version is lower
than the one the label shows, or when the element is not marked the way this
script expects: an unknown tool or format, anything but text inside, or text
that does not hold exactly one version of that format. The other labels are
still filled. A label listed in SPOTS that has lost its marker is reported as
well. The first line printed says which versions were read and how many labels
changed. If anything above happened, one warning line follows it with every
reason, and the exit code is still 0.
"""
import http.client
import json
import os
import pathlib
import re
import shutil
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

sys.dont_write_bytecode = True  # importing build_pulse leaves no __pycache__ folder in the repository
from build_pulse import OPENER, TIMEOUT, Unavailable  # noqa: E402

SAST, SCA = "sast-triage", "sca-triage"
REGISTRY = "https://registry.npmjs.org"
MAX_ANSWER_BYTES = 4 * 1024 * 1024  # a longer registry answer is treated as a failure
NUMBER = "(0|[1-9][0-9]{0,8})"  # no leading zeros, and no number too long to be a version
VERSION = re.compile(rf"{NUMBER}\.{NUMBER}\.{NUMBER}")
# Each format, with how many numbers of the version it shows.
FORMATS = {"X.Y.Z": 3, "X.Y": 2}
SHOWN = {name: re.compile(r"\.".join([NUMBER] * count)) for name, count in FORMATS.items()}
DOTTED = re.compile(r"[0-9]+(?:\.[0-9]+)*")  # every run of numbers and dots in a label's text
# The labels the site has now: page, tool, format, how many. A page with fewer is reported.
SPOTS = (("index.html", SAST, "X.Y.Z", 1), ("index.html", SCA, "X.Y.Z", 1),
         ("sast-triage.html", SAST, "X.Y", 2), ("sast-triage.html", SAST, "X.Y.Z", 1))


def numbers(version):
    """Returns "2.5.0" as (2, 5, 0), so versions compare by number and not as text."""
    return tuple(int(part) for part in version.split("."))


def sast_version(site):
    """Returns the highest sast-triage version in the site's pulse data."""
    target = site / "data" / "pulse.json"
    try:
        releases = json.loads(target.read_bytes())["releases"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Unavailable(f"{target} cannot be read as pulse data") from None
    if not isinstance(releases, list):
        raise Unavailable(f"{target} cannot be read as pulse data")
    found = [numbers(r["version"]) for r in releases
             if isinstance(r, dict) and r.get("tool") == SAST
             and isinstance(r.get("version"), str) and VERSION.fullmatch(r["version"])]
    if not found:
        raise Unavailable(f"{target} holds no {SAST} release")
    return max(found)


def sca_version():
    """Returns dist-tags.latest of sca-triage in the npm registry."""
    request = urllib.request.Request(f"{REGISTRY}/{SCA}", headers={
        "Accept": "application/vnd.npm.install-v1+json", "User-Agent": "dotrobin-dev-build-versions"})
    try:
        with OPENER.open(request, timeout=TIMEOUT) as response:
            body = response.read(MAX_ANSWER_BYTES + 1)
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        raise Unavailable(f"the npm registry answered HTTP {code} for {SCA}"
                          + (" (rate limit reached)" if code == 429 else "")) from None
    except (OSError, http.client.HTTPException) as error:
        raise Unavailable(f"the npm registry could not be reached for {SCA} ({type(error).__name__})") from None
    if len(body) > MAX_ANSWER_BYTES:
        raise Unavailable(f"the npm registry's answer for {SCA} is larger than {MAX_ANSWER_BYTES} bytes")
    try:
        package = json.loads(body)
    except ValueError:
        raise Unavailable(f"the npm registry's answer for {SCA} is not valid JSON") from None
    if not isinstance(package, dict) or package.get("name") != SCA:
        raise Unavailable(f"the npm registry's answer is not the {SCA} package")
    tags = package.get("dist-tags")
    latest = tags.get("latest") if isinstance(tags, dict) else None
    if not isinstance(latest, str) or not VERSION.fullmatch(latest):
        raise Unavailable(f"the npm registry's latest version of {SCA} is not X.Y.Z")
    return numbers(latest)


class Label:
    """One marked element: its markers, and where its content starts and ends in the page."""

    def __init__(self, tag, line, tool, shown, start):
        self.tag, self.line, self.tool, self.shown, self.start = tag, line, tool, shown, start
        self.end, self.problem = None, None


class Labels(HTMLParser):
    """Finds the marked elements of one page.

    A marked element must hold text and nothing else, so the first thing
    after its start tag that is not text has to be its own end tag.
    """

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.found, self.open = [], None
        self.line_starts = [0] + [at + 1 for at, char in enumerate(text) if char == "\n"]
        self.feed(text)
        self.close()
        self.shut("is never closed")

    def here(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def shut(self, problem):
        if self.open:
            self.open.problem, self.open = problem, None

    def handle_starttag(self, tag, attrs):
        self.shut("holds more than text")
        marks = dict(attrs)
        if "data-release" in marks or "data-release-format" in marks:
            self.open = Label(tag, self.getpos()[0], marks.get("data-release"),
                              marks.get("data-release-format"), self.here() + len(self.get_starttag_text()))
            self.found.append(self.open)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.shut("holds no text")

    def handle_endtag(self, tag):
        if self.open and self.open.tag == tag:
            self.open.end, self.open = self.here(), None
        else:
            self.shut("holds more than text")

    def other(self, *_):
        self.shut("holds more than text")

    handle_entityref = handle_charref = handle_comment = handle_decl = handle_pi = unknown_decl = other


def fill(name, text, versions):
    """Returns the page text with its labels filled, the labels, what went wrong and how many changed."""
    labels, problems, changes = Labels(text).found, [], []
    for label in labels:
        where = f"{name} line {label.line}: the <{label.tag}> marked as a version label"
        tokens = [] if label.end is None else list(DOTTED.finditer(text, label.start, label.end))
        if label.problem:
            problems.append(f"{where} {label.problem}")
        elif label.tool not in (SAST, SCA):
            problems.append(f"{where} names no known tool in data-release")
        elif label.shown not in FORMATS:
            problems.append(f"{where} has no data-release-format of {' or '.join(FORMATS)}")
        elif len(tokens) != 1 or not SHOWN[label.shown].fullmatch(tokens[0][0]):
            problems.append(f"{where} does not hold exactly one {label.shown} version")
        elif label.tool in versions:
            current = versions[label.tool][:FORMATS[label.shown]]
            committed = numbers(tokens[0][0])
            if current < committed:
                problems.append(f"{name} line {label.line}: {label.tool} {'.'.join(map(str, current))} is lower"
                                f" than the committed {tokens[0][0]}")
            elif current > committed:
                changes.append((tokens[0].start(), tokens[0].end(), ".".join(map(str, current))))
    for start, end, version in reversed(changes):
        text = text[:start] + version + text[end:]
    return text, labels, problems, len(changes)


def write(target, text):
    """Replaces the page in one step, so a write that fails leaves the old page whole."""
    draft = target.with_name(target.name + ".tmp")
    try:
        with open(draft, "wb") as f:
            f.write(text.encode("utf-8"))
        shutil.copymode(target, draft)  # Pages only serves a file that everyone may read
        os.replace(draft, target)
    except OSError as error:
        raise Unavailable(f"{target} could not be written ({type(error).__name__})") from None
    finally:
        draft.unlink(missing_ok=True)


def build(site):
    """Fills the labels of every page.

    Returns the versions read, how many labels changed, how many there are, and the problems.
    """
    versions, problems, changed = {}, [], 0
    for tool, read in ((SAST, lambda: sast_version(site)), (SCA, sca_version)):
        try:
            versions[tool] = read()
        except Unavailable as error:
            problems.append(str(error))
    marked = {}
    for page in sorted(site.rglob("*.html")):
        name = page.relative_to(site).as_posix()
        try:
            before = page.read_bytes().decode("utf-8")
            after, labels, wrong, count = fill(name, before, versions)
            if after != before:
                write(page, after)
                changed += count
        except (OSError, UnicodeDecodeError) as error:
            problems.append(f"{name} could not be read ({type(error).__name__})")
            continue
        except Unavailable as error:
            wrong.append(str(error))
        problems += wrong
        for label in labels:
            marked[name, label.tool, label.shown] = marked.get((name, label.tool, label.shown), 0) + 1
    for name, tool, shown, count in SPOTS:
        if marked.get((name, tool, shown), 0) < count:
            problems.append(f"{name}: {marked.get((name, tool, shown), 0)} of {count} {tool} {shown} label(s)"
                            " carry the data-release marker")
    return versions, changed, sum(marked.values()), problems


def main():
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    try:
        versions, changed, total, problems = build(site)
    except Exception as error:  # whatever went wrong, the deploy goes on with the pages as they are
        # Only the kind of an unexpected error is printed: its text could quote the data that caused it.
        versions, changed, total, problems = {}, 0, 0, [f"unexpected {type(error).__name__}"]
    read = ", ".join(f"{tool} {'.'.join(map(str, versions[tool]))}" for tool in (SAST, SCA) if tool in versions)
    print(f"{site}: {changed} of {total} version labels changed ({read or 'no version read'})")
    if problems:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "warning: "
        # One line whatever a page or a file name holds, so the text cannot start a workflow command.
        reasons = "".join(char if char.isprintable() else "?" for char in "; ".join(problems))
        print(f"{prefix}version labels not all filled, the committed text stays where one was not: {reasons}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
