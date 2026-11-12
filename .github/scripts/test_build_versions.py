#!/usr/bin/env python3
"""Tests for build_versions.py. Standard library only. Neither npm nor GitHub is contacted.

Usage: python3 .github/scripts/test_build_versions.py

FakeNpm answers the script's request the way registry.npmjs.org does, and the
pulse data is a file the test writes the way build_pulse.py does. Most tests
run the script on a small site with five labels written like the real ones. The
last class runs it on a copy of the committed pages, which hold six.
"""
import contextlib
import email.message
import http.client
import io
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.dont_write_bytecode = True  # leave no __pycache__ folder in the repository
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_pulse  # noqa: E402
import build_versions  # noqa: E402

SITE = pathlib.Path(__file__).resolve().parents[2] / "site"
SAST, SCA = "sast-triage", "sca-triage"
TOKEN = "token-that-must-not-be-printed"
WARNING = re.compile(r"\Awarning: version labels not all filled, the committed text stays where one was not: .+\Z")

# The five labels, written the way the site writes them.
CARD_SCA = '<span class="bento-version" data-release="sca-triage" data-release-format="X.Y.Z">Version {card_sca}</span>'
CARD_SAST = ('<span class="bento-version" data-release="sast-triage" data-release-format="X.Y.Z">'
             'Version {card_sast}</span>')
LINK = ('<strong class="resource-title" data-release="sast-triage" data-release-format="X.Y">'
        'Version {link} on GitHub</strong>')
NOTICE = '<strong data-release="sast-triage" data-release-format="X.Y">Version {notice}</strong>'
ACTION = ('- uses: lansiquo/sast-triage@v<span data-release="sast-triage" data-release-format="X.Y.Z">'
          '{action}</span>')
SPOTS = {"card_sca": ("index.html", CARD_SCA), "card_sast": ("index.html", CARD_SAST),
         "link": ("sast-triage.html", LINK), "notice": ("sast-triage.html", NOTICE),
         "action": ("sast-triage.html", ACTION)}
MARKER = re.compile(r' data-release="[a-z-]+" data-release-format="[XYZ.]+"')
INDEX = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Home</title></head><body>'
         '<article><code class="bento-command">$ npx sca-triage</code><div class="bento-actions">' + CARD_SCA
         + '<a class="bento-link" href="https://www.npmjs.com/package/sca-triage">npm</a></div></article>'
         '<article><p>Python · Semgrep 1.79.0</p><div class="bento-actions">' + CARD_SAST
         + '</div></article></body></html>\n')
SAST_PAGE = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>sast-triage</title></head><body>'
             '<a href="https://github.com/lansiquo/sast-triage">' + LINK + '</a><p class="notice">' + NOTICE
             + ' runs locally and as a GitHub Action.</p>\n'
             '<p class="evidence-note">Checked on sast-triage v2.1.1 (<code>9b5e308</code>): 197 tests passed.</p>\n'
             '<pre tabindex="0"><code>- uses: actions/checkout@v4\n  with:\n    fetch-depth: 0\n' + ACTION
             + '</code></pre>\n</body></html>\n')
SCA_PAGE = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>sca-triage</title></head><body>'
            '<p class="evidence-note">Checked on the current release, <a href="https://github.com/lansiquo/'
            'sca-triage/tree/v1.2.4"><code>v1.2.4</code></a>: all 96 tests pass.</p>\n</body></html>\n')


def site_pages(card_sca="1.2.4", card_sast="2.5.0", link="2.5", notice="2.5", action="2.5.0", change=None):
    """The pages of the small site, as bytes, with these versions in the five labels.

    `change` maps the name of a label (a key of SPOTS) to a function that
    rewrites its markup, to build a page whose label is not as expected.
    """
    shown = {"card_sca": card_sca, "card_sast": card_sast, "link": link, "notice": notice, "action": action}
    pages = {"index.html": INDEX, "sast-triage.html": SAST_PAGE, "sca-triage.html": SCA_PAGE}
    for spot, rewrite in (change or {}).items():
        name, markup = SPOTS[spot]
        assert pages[name].count(markup) == 1
        pages[name] = pages[name].replace(markup, rewrite(markup))
    return {name: text.format(**shown).encode() for name, text in pages.items()}


def pulse_file(*versions, tool=SAST):
    """The bytes of a pulse.json that holds these versions of one tool, in the order given."""
    releases = [{"published": f"2026-11-{day:02}T12:00:00Z", "tool": tool, "version": version}
                for day, version in enumerate(versions, 1)]
    return (json.dumps({"generated": "2026-11-12T14:00:00Z", "releases": releases}, indent=2) + "\n").encode()


def package(latest, *versions):
    """The sca-triage package as the registry sends it in its short form."""
    listed = {v: {"name": SCA, "version": v, "dist": {"tarball": f"https://registry.npmjs.org/{SCA}/-/{SCA}-{v}.tgz"}}
              for v in versions or (latest,)}
    return json.dumps({"name": SCA, "dist-tags": {"latest": latest}, "versions": listed,
                       "modified": "2026-11-12T14:00:00.000Z"}).encode()


def http_error(code):
    return urllib.error.HTTPError("https://registry.npmjs.org/", code, "error", email.message.Message(),
                                  io.BytesIO(b'{"error": "error"}'))


class Answer:
    """A successful answer, as urllib hands it to the script."""

    def __init__(self, body):
        self.body = body

    def read(self, amount=-1):
        return self.body if amount < 0 else self.body[:amount]

    def __enter__(self):
        return self

    def __exit__(self, *error):
        return False


class FakeNpm:
    """Stands in for registry.npmjs.org.

    `latest` is the dist-tags.latest of sca-triage. `instead` is an exception
    to raise, or the bytes to send, in place of the package. Any other address
    gets HTTP 404. Every request is kept in `requests` with its timeout.
    """

    def __init__(self, latest="1.2.4", instead=None):
        self.latest, self.instead, self.requests = latest, instead, []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        if request.full_url != "https://registry.npmjs.org/sca-triage":
            raise http_error(404)
        if isinstance(self.instead, Exception):
            raise self.instead
        return Answer(package(self.latest) if self.instead is None else self.instead)


class Result:
    def __init__(self, code, output, pages, modes):
        self.code, self.output, self.pages, self.modes = code, output, pages, modes


def run(pages=None, pulse=pulse_file("2.5.0"), npm=None, env=None, modes=None):
    """Runs the script on a site that holds `pages` and the pulse data `pulse`.

    `npm` answers the request; without it the registry reports 1.2.4. With
    `pulse` None the site has no pulse.json. `modes` sets the permission bits
    of pages before the run. The result holds every file of the site after
    the run except pulse.json. GITHUB_TOKEN and GITHUB_ACTIONS are unset
    unless `env` sets them, so the result is the same on a laptop and in CI.
    """
    environment = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GITHUB_ACTIONS")}
    environment.update(env or {})
    with tempfile.TemporaryDirectory() as site:
        root = pathlib.Path(site)
        (root / "data").mkdir()
        if pulse is not None:
            (root / "data" / "pulse.json").write_bytes(pulse)
        for name, content in (site_pages() if pages is None else pages).items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(content)
            if modes and name in modes:
                (root / name).chmod(modes[name])
        out = io.StringIO()
        with mock.patch.object(build_versions.OPENER, "open", (npm or FakeNpm()).open), \
                mock.patch.object(sys, "argv", ["build_versions.py", site]), \
                mock.patch.dict(os.environ, environment, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = build_versions.main()
        files = [p for p in sorted(root.rglob("*")) if p.is_file() and p.name != "pulse.json"]
        after = {p.relative_to(root).as_posix(): p.read_bytes() for p in files}
        modes = {p.relative_to(root).as_posix(): stat.S_IMODE(p.stat().st_mode) for p in files}
    return Result(code, out.getvalue(), after, modes)


class Case(unittest.TestCase):
    maxDiff = None

    def assert_filled(self, result, pages, changed):
        """The run ended well: one line that is not a warning, and the site holds exactly `pages`."""
        self.assertEqual(result.code, 0)
        self.assertRegex(result.output, rf"\A[^\n]+: {changed} of [0-9]+ version labels changed \([^\n]+\)\n\Z")
        self.assertNotIn("warning", result.output)
        self.assertEqual(result.pages, pages)

    def assert_warned(self, result, pages, *reasons):
        """The run ended with exit code 0 and one warning line, and the site holds exactly `pages`.

        The warning follows the line that says what was read and changed.
        """
        self.assertEqual(result.code, 0)
        self.assertEqual(result.output.count("\n"), 2, result.output)
        summary, warning = result.output.splitlines()
        self.assertRegex(summary, r"\A.+: [0-9]+ of [0-9]+ version labels changed \(.+\)\Z")
        self.assertNotIn("warning", summary)
        self.assertRegex(warning, WARNING)
        for reason in reasons:
            self.assertIn(reason, result.output)
        self.assertEqual(result.pages, pages)


class FillTest(Case):
    def test_the_homepage_sast_triage_card_shows_the_release(self):
        result = run(site_pages(card_sast="2.4.1"), pulse=pulse_file("2.4.1", "2.5.0"))
        self.assert_filled(result, site_pages(card_sast="2.5.0"), 1)
        self.assertIn(b">Version 2.5.0</span></div></article></body>", result.pages["index.html"])

    def test_the_homepage_sca_triage_card_shows_npm_latest(self):
        result = run(site_pages(card_sca="1.2.3"), npm=FakeNpm("1.2.4"))
        self.assert_filled(result, site_pages(card_sca="1.2.4"), 1)
        self.assertIn(b'data-release-format="X.Y.Z">Version 1.2.4</span><a class="bento-link"',
                      result.pages["index.html"])

    def test_the_link_to_github_shows_major_and_minor(self):
        result = run(site_pages(link="2.4"), pulse=pulse_file("2.5.0"))
        self.assert_filled(result, site_pages(link="2.5"), 1)
        self.assertIn(b">Version 2.5 on GitHub</strong></a>", result.pages["sast-triage.html"])

    def test_the_notice_shows_major_and_minor(self):
        result = run(site_pages(notice="2.4"), pulse=pulse_file("2.5.0"))
        self.assert_filled(result, site_pages(notice="2.5"), 1)
        self.assertIn(b">Version 2.5</strong> runs locally", result.pages["sast-triage.html"])

    def test_the_action_example_pins_the_release(self):
        result = run(site_pages(action="2.4.1"), pulse=pulse_file("2.5.0"))
        self.assert_filled(result, site_pages(action="2.5.0"), 1)
        self.assertIn(b'- uses: lansiquo/sast-triage@v<span data-release="sast-triage" data-release-format="X.Y.Z">'
                      b"2.5.0</span></code></pre>", result.pages["sast-triage.html"])
        self.assertIn(b"- uses: actions/checkout@v4\n", result.pages["sast-triage.html"])

    def test_all_five_labels_are_filled_in_one_run_and_nothing_else_changes(self):
        result = run(site_pages("1.2.3", "2.4.1", "2.4", "2.4", "2.4.1"),
                     pulse=pulse_file("2.4.1", "3.10.2"), npm=FakeNpm("1.3.0"))
        self.assert_filled(result, site_pages("1.3.0", "3.10.2", "3.10", "3.10", "3.10.2"), 5)
        self.assertEqual(result.output.split(": ", 1)[1],
                         "5 of 5 version labels changed (sast-triage 3.10.2, sca-triage 1.3.0)\n")

    def test_statements_about_a_checked_version_are_never_rewritten(self):
        result = run(pulse=pulse_file("9.9.9"), npm=FakeNpm("9.9.9"))
        self.assertEqual(result.pages["sca-triage.html"], SCA_PAGE.encode())
        self.assertIn(b"Checked on sast-triage v2.1.1 (<code>9b5e308</code>): 197 tests passed.",
                      result.pages["sast-triage.html"])
        self.assertIn(b"- uses: actions/checkout@v4\n", result.pages["sast-triage.html"])
        self.assertIn(b"Semgrep 1.79.0", result.pages["index.html"])

    def test_the_sast_triage_version_is_the_highest_release_not_the_last_one_published(self):
        for versions, highest in ((("2.5.0", "2.4.2"), "2.5.0"), (("2.9.0", "2.10.0", "2.9.5"), "2.10.0"),
                                  (("2.5.0", "10.0.0", "9.9.9"), "10.0.0")):
            with self.subTest(versions=versions):
                result = run(site_pages(card_sast="2.4.1"), pulse=pulse_file(*versions))
                self.assert_filled(result, site_pages(card_sast=highest, action=highest,
                                                      link=highest.rsplit(".", 1)[0],
                                                      notice=highest.rsplit(".", 1)[0]), "[1-4]")

    def test_releases_of_the_other_tool_and_entries_that_do_not_validate_are_skipped(self):
        data = json.loads(pulse_file("2.5.0"))
        data["releases"] += [{"published": "2026-11-12T13:29:15Z", "tool": SCA, "version": "8.0.0"},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST, "version": "v9.0.0"},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST, "version": "9.0"},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST, "version": "09.0.0"},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST, "version": "9.0.0-rc.1"},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST, "version": 900},
                             {"published": "2026-11-12T13:29:15Z", "tool": SAST}, "9.0.0", None]
        result = run(site_pages(card_sast="2.4.1"), pulse=json.dumps(data).encode())
        self.assert_filled(result, site_pages(), 1)

    def test_the_sca_triage_version_is_npm_latest_not_the_highest_published_or_released(self):
        npm = FakeNpm(instead=package("1.2.4", "1.2.3", "1.2.4", "1.3.0"))
        result = run(site_pages(card_sca="1.2.3"), pulse=pulse_file("2.5.0"), npm=npm)
        self.assert_filled(result, site_pages(card_sca="1.2.4"), 1)

    def test_one_request_goes_to_the_npm_registry_without_a_token(self):
        npm = FakeNpm("1.2.4")
        result = run(npm=npm, env={"GITHUB_TOKEN": TOKEN})
        self.assert_filled(result, site_pages(), 0)
        self.assertEqual(len(npm.requests), 1)
        request, timeout = npm.requests[0]
        self.assertEqual(request.full_url, "https://registry.npmjs.org/sca-triage")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, build_versions.TIMEOUT)
        self.assertNotIn("authorization", {name.lower() for name, _ in request.header_items()})
        self.assertNotIn(TOKEN, repr(request.header_items()) + result.output)
        self.assertIs(build_versions.OPENER, build_pulse.OPENER)  # the opener that follows no redirect

    def test_a_page_keeps_its_permissions_and_no_other_file_appears(self):
        for mode in (0o644, 0o640):
            with self.subTest(mode=oct(mode)):
                result = run(site_pages(card_sast="2.4.1"), modes={"index.html": mode})
                self.assert_filled(result, site_pages(), 1)
                self.assertEqual(result.modes["index.html"], mode)

    def test_a_label_on_any_page_of_the_site_is_filled(self):
        extra = '<!doctype html><title>t</title><p data-release="sca-triage" data-release-format="X.Y">npm {}.</p>\n'
        result = run({**site_pages(), "notes/more.html": extra.format("1.1").encode()}, npm=FakeNpm("1.2.4"))
        self.assert_filled(result, {**site_pages(), "notes/more.html": extra.format("1.2").encode()}, 1)

    def test_markup_inside_a_comment_or_a_script_is_not_a_label(self):
        label = CARD_SAST.format(card_sast="1.0.0")
        page = f"<!doctype html><title>t</title><!-- {label} --><script>var a = '{label}';</script>\n".encode()
        result = run({**site_pages(), "other.html": page}, pulse=pulse_file("2.5.0"))
        self.assert_filled(result, {**site_pages(), "other.html": page}, 0)


class NeverLowerTest(Case):
    def test_a_version_lower_than_the_committed_one_keeps_the_committed_text(self):
        result = run(pulse=pulse_file("2.4.9"), npm=FakeNpm("1.2.3"))
        self.assert_warned(result, site_pages(),
                           "index.html line 1: sast-triage 2.4.9 is lower than the committed 2.5.0",
                           "index.html line 1: sca-triage 1.2.3 is lower than the committed 1.2.4",
                           "sast-triage.html line 1: sast-triage 2.4 is lower than the committed 2.5",
                           "sast-triage.html line 6: sast-triage 2.4.9 is lower than the committed 2.5.0")

    def test_versions_are_compared_as_numbers(self):
        raised = run(site_pages("1.9.0", "2.9.0", "2.9", "2.9", "2.9.9"),
                     pulse=pulse_file("2.10.0"), npm=FakeNpm("1.10.0"))
        self.assert_filled(raised, site_pages("1.10.0", "2.10.0", "2.10", "2.10", "2.10.0"), 5)
        committed = site_pages("1.10.0", "2.10.0", "2.10", "2.10", "2.10.0")
        kept = run(committed, pulse=pulse_file("2.9.9"), npm=FakeNpm("1.9.9"))
        self.assert_warned(kept, committed, "sast-triage 2.9.9 is lower than the committed 2.10.0",
                           "sast-triage 2.9 is lower than the committed 2.10",
                           "sca-triage 1.9.9 is lower than the committed 1.10.0")

    def test_the_same_version_changes_nothing(self):
        self.assert_filled(run(), site_pages(), 0)

    def test_a_patch_release_leaves_the_major_and_minor_labels_as_they_are(self):
        result = run(pulse=pulse_file("2.5.0", "2.5.3"))
        self.assert_filled(result, site_pages(card_sast="2.5.3", action="2.5.3"), 2)

    def test_each_label_is_compared_with_its_own_committed_text(self):
        committed = site_pages(card_sast="2.6.0", link="2.4", notice="2.6", action="2.4.1")
        result = run(committed, pulse=pulse_file("2.5.3"))
        self.assert_warned(result, site_pages(card_sast="2.6.0", link="2.5", notice="2.6", action="2.5.3"),
                           "index.html line 1: sast-triage 2.5.3 is lower than the committed 2.6.0",
                           "sast-triage.html line 1: sast-triage 2.5 is lower than the committed 2.6")


class FailureTest(Case):
    def test_a_failed_npm_request_keeps_the_sca_triage_label(self):
        failures = [
            (urllib.error.URLError("no route to host"),
             "the npm registry could not be reached for sca-triage (URLError)"),
            (TimeoutError("timed out"), "could not be reached for sca-triage (TimeoutError)"),
            (ConnectionResetError("reset"), "could not be reached for sca-triage (ConnectionResetError)"),
            (http.client.RemoteDisconnected("closed"), "could not be reached for sca-triage (RemoteDisconnected)"),
            (http.client.IncompleteRead(b"{"), "could not be reached for sca-triage (IncompleteRead)"),
            (http_error(404), "the npm registry answered HTTP 404 for sca-triage"),
            (http_error(500), "the npm registry answered HTTP 500 for sca-triage"),
            (http_error(503), "the npm registry answered HTTP 503 for sca-triage"),
            (http_error(429), "the npm registry answered HTTP 429 for sca-triage (rate limit reached)"),
        ]
        for failure, reason in failures:
            with self.subTest(reason=reason):
                result = run(site_pages(card_sca="1.2.3", card_sast="2.4.1"), npm=FakeNpm(instead=failure))
                self.assert_warned(result, site_pages(card_sca="1.2.3"), reason)
                self.assertNotIn("no route to host", result.output)

    def test_an_npm_answer_that_is_not_the_expected_data_keeps_the_sca_triage_label(self):
        def tagged(latest):
            return json.dumps({"name": SCA, "dist-tags": {"latest": latest}}).encode()

        not_a_version = "the npm registry's latest version of sca-triage is not X.Y.Z"
        not_the_package = "the npm registry's answer is not the sca-triage package"
        answers = [
            (b"<html>Service unavailable</html>", "the npm registry's answer for sca-triage is not valid JSON"),
            (b"", "is not valid JSON"),
            (b"\xff\xfe", "is not valid JSON"),
            (b"[]", not_the_package),
            (b'"1.2.5"', not_the_package),
            (b"{}", not_the_package),
            (json.dumps({"name": "sca-triage-evil", "dist-tags": {"latest": "9.9.9"}}).encode(), not_the_package),
            (json.dumps({"name": SCA}).encode(), not_a_version),
            (json.dumps({"name": SCA, "dist-tags": ["1.2.5"]}).encode(), not_a_version),
            (json.dumps({"name": SCA, "dist-tags": {"next": "1.2.5"}}).encode(), not_a_version),
            (b" " * (build_versions.MAX_ANSWER_BYTES + 1), "is larger than 4194304 bytes"),
        ]
        answers += [(tagged(latest), not_a_version) for latest in (
            "1.2", "1.2.5.0", "v1.2.5", "1.2.5-beta.1", "1.2.5+build", "1.2.5 ", " 1.2.5", "1.2.5\n", "01.2.5",
            "1.02.5", "1.2.x", "", "latest", "1.2.5\n::error::stop", "1." + "9" * 5000 + ".0", 125, 1.2, None,
            ["1.2.5"], {"version": "1.2.5"})]
        for body, reason in answers:
            with self.subTest(body=body[:60]):
                result = run(site_pages(card_sca="1.2.3", card_sast="2.4.1"), npm=FakeNpm(instead=body))
                self.assert_warned(result, site_pages(card_sca="1.2.3"), reason)
                self.assertNotIn("::error::", result.output)

    def test_pulse_data_that_cannot_be_used_keeps_the_sast_triage_labels(self):
        def held(*releases):
            return json.dumps({"generated": "2026-11-12T14:00:00Z", "releases": list(releases)}).encode()

        unreadable, none = "pulse.json cannot be read as pulse data", "pulse.json holds no sast-triage release"
        files = [
            (None, unreadable), (b"", unreadable), (b"not json", unreadable), (b"\xff\xfe", unreadable),
            (b"[]", unreadable), (b"7", unreadable), (b"{}", unreadable), (b'{"releases": 5}', unreadable),
            (b'{"releases": {"sast-triage": "2.6.0"}}', unreadable),
            (held(), none),
            (pulse_file("1.3.0", tool=SCA), none),
            (held({"tool": SAST, "version": "v2.6.0"}, {"tool": SAST, "version": "2.6"},
                  {"tool": SAST, "version": "02.6.0"}, {"tool": SAST, "version": "2.6.0\n::error::stop"},
                  {"tool": SAST, "version": 260}, {"tool": SAST}, {"tool": "sast", "version": "2.6.0"},
                  "2.6.0", ["sast-triage", "2.6.0"], None), none),
        ]
        committed = site_pages("1.2.3", "2.4.1", "2.4", "2.4", "2.4.1")
        for pulse, reason in files:
            with self.subTest(pulse=pulse and pulse[:60]):
                result = run(committed, pulse=pulse, npm=FakeNpm("1.2.4"))
                self.assert_warned(result, site_pages("1.2.4", "2.4.1", "2.4", "2.4", "2.4.1"), reason)
                self.assertNotIn("::error::", result.output)

    def test_when_neither_version_can_be_read_every_page_stays_as_committed(self):
        committed = site_pages("1.2.3", "2.4.1", "2.4", "2.4", "2.4.1")
        result = run(committed, pulse=None, npm=FakeNpm(instead=http_error(429)))
        self.assert_warned(result, committed, "pulse.json cannot be read as pulse data",
                           "the npm registry answered HTTP 429 for sca-triage (rate limit reached)")
        self.assertIn(": 0 of 5 version labels changed (no version read)\n", result.output)

    def test_the_first_line_names_the_version_that_was_read_when_the_other_was_not(self):
        committed = site_pages("1.2.3", "2.4.1", "2.4", "2.4", "2.4.1")
        without_npm = run(committed, npm=FakeNpm(instead=http_error(503)))
        self.assertIn(": 4 of 5 version labels changed (sast-triage 2.5.0)\n", without_npm.output)
        without_pulse = run(committed, pulse=None)
        self.assertIn(": 1 of 5 version labels changed (sca-triage 1.2.4)\n", without_pulse.output)

    def test_a_label_that_lost_its_marker_is_reported_and_keeps_its_text(self):
        old = dict(card_sca="1.2.3", card_sast="2.4.1", link="2.4", notice="2.4", action="2.4.1")
        new = dict(card_sca="1.2.4", card_sast="2.5.0", link="2.5", notice="2.5", action="2.5.0")
        reasons = {"card_sca": "index.html: 0 of 1 sca-triage X.Y.Z label(s) carry the data-release marker",
                   "card_sast": "index.html: 0 of 1 sast-triage X.Y.Z label(s) carry the data-release marker",
                   "link": "sast-triage.html: 1 of 2 sast-triage X.Y label(s) carry the data-release marker",
                   "notice": "sast-triage.html: 1 of 2 sast-triage X.Y label(s) carry the data-release marker",
                   "action": "sast-triage.html: 0 of 1 sast-triage X.Y.Z label(s) carry the data-release marker"}
        for spot, reason in reasons.items():
            with self.subTest(spot=spot):
                change = {spot: lambda markup: MARKER.sub("", markup)}
                result = run(site_pages(**old, change=change))
                self.assert_warned(result, site_pages(**{**new, spot: old[spot]}, change=change), reason)

    def test_a_page_that_is_missing_is_reported(self):
        pages = site_pages(card_sca="1.2.3", action="2.4.1")
        del pages["index.html"]
        filled = site_pages()
        del filled["index.html"]
        self.assert_warned(run(pages), filled,
                           "index.html: 0 of 1 sast-triage X.Y.Z label(s) carry the data-release marker",
                           "index.html: 0 of 1 sca-triage X.Y.Z label(s) carry the data-release marker")

    def test_a_label_that_is_not_marked_as_expected_keeps_its_text(self):
        def swap(old, new):
            return lambda markup: markup.replace(old, new, 1) if old in markup else self.fail(old)

        label = "the <span> marked as a version label"
        changes = [
            (swap('data-release="sast-triage"', 'data-release="semgrep"'),
             f"{label} names no known tool in data-release"),
            (swap('data-release="sast-triage"', 'data-release=""'), f"{label} names no known tool"),
            (swap('data-release="sast-triage" ', ""), f"{label} names no known tool"),
            (swap(' data-release-format="X.Y.Z"', ""), f"{label} has no data-release-format of X.Y.Z or X.Y"),
            (swap('"X.Y.Z"', '"vX.Y.Z"'), f"{label} has no data-release-format of X.Y.Z or X.Y"),
            (swap('"X.Y.Z"', '"x.y.z"'), f"{label} has no data-release-format"),
            (swap('"X.Y.Z"', '"X"'), f"{label} has no data-release-format"),
            (swap('"X.Y.Z"', '"X.Y"'), f"{label} does not hold exactly one X.Y version"),
            (swap("Version {card_sast}", "Version <b>{card_sast}</b>"), f"{label} holds more than text"),
            (swap("Version {card_sast}", "Version&nbsp;{card_sast}"), f"{label} holds more than text"),
            (swap("Version {card_sast}", "Version&#32;{card_sast}"), f"{label} holds more than text"),
            (swap("Version {card_sast}", "Version <!-- now -->{card_sast}"), f"{label} holds more than text"),
            (swap("Version {card_sast}", "Version {card_sast}<br>"), f"{label} holds more than text"),
            (swap("</span>", "</strong>"), f"{label} holds more than text"),
            (swap("</span>", ""), f"{label} holds more than text"),
            (swap("Version {card_sast}", "Version"), f"{label} does not hold exactly one X.Y.Z version"),
            (swap("Version {card_sast}", ""), f"{label} does not hold exactly one X.Y.Z version"),
            (swap("Version {card_sast}", "Version 2.4"), f"{label} does not hold exactly one X.Y.Z version"),
            (swap("Version {card_sast}", "Version 2.4.1.0"), f"{label} does not hold exactly one X.Y.Z version"),
            (swap("Version {card_sast}", "Version 02.4.1"), f"{label} does not hold exactly one X.Y.Z version"),
            (swap("Version {card_sast}", "Version {card_sast} (was 2.4.0)"), f"{label} does not hold exactly one"),
            (swap("Version {card_sast}", "Version {card_sast} of 3"), f"{label} does not hold exactly one"),
            (swap(">Version {card_sast}</span>", "/>Version {card_sast}"), f"{label} holds no text"),
        ]
        for rewrite, reason in changes:
            change = {"card_sast": rewrite}
            with self.subTest(markup=rewrite(CARD_SAST)):
                result = run(site_pages("1.2.3", "2.4.1", "2.4", "2.4", "2.4.1", change=change))
                self.assert_warned(result, site_pages("1.2.4", "2.4.1", "2.5", "2.5", "2.5.0", change=change),
                                   f"index.html line 1: {reason}")

    def test_a_label_left_open_at_the_end_of_the_page_keeps_its_text(self):
        page = b'<!doctype html><title>t</title><p data-release="sca-triage" data-release-format="X.Y.Z">npm 1.2.3'
        result = run({**site_pages(), "open.html": page}, npm=FakeNpm("1.2.4"))
        self.assert_warned(result, {**site_pages(), "open.html": page},
                           "open.html line 1: the <p> marked as a version label is never closed")

    def test_a_page_that_is_not_utf8_is_reported_and_the_others_are_filled(self):
        pages = {**site_pages(card_sca="1.2.3"), "latin.html": b"<!doctype html><title>caf\xe9</title>\n"}
        result = run(pages)
        self.assert_warned(result, {**pages, **site_pages()}, "latin.html could not be read (UnicodeDecodeError)")

    def test_a_failed_write_keeps_the_page(self):
        committed = site_pages(card_sast="2.4.1")
        with mock.patch.object(build_versions.os, "replace", side_effect=PermissionError("read-only")):
            result = run(committed)
        self.assert_warned(result, committed, "index.html could not be written (PermissionError)")
        self.assertNotIn("read-only", result.output)

    def test_an_unexpected_error_still_ends_with_a_warning_and_exit_code_0(self):
        committed = site_pages(card_sast="2.4.1")
        with mock.patch.object(build_versions, "fill", side_effect=RuntimeError(f"text with {TOKEN}")):
            result = run(committed, env={"GITHUB_TOKEN": TOKEN})
        self.assert_warned(result, committed, "unexpected RuntimeError")
        self.assertNotIn(TOKEN, result.output)

    def test_in_github_actions_the_warning_is_an_annotation(self):
        result = run(pulse=None, env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(result.code, 0)
        self.assertRegex(result.output, r"\A[^\n]+\n::warning::version labels not all filled, [^\n]+\n\Z")
        self.assertEqual(result.output.count("::warning::"), 1)

    def test_the_warning_is_one_line_whatever_a_file_name_holds(self):
        if os.name == "nt":
            self.skipTest("a file name cannot hold a line break on Windows")
        name = "a\n::error::stop.html"
        pages = {**site_pages(), name: b"<!doctype html><title>caf\xe9</title>\n"}
        result = run(pages)
        self.assert_warned(result, pages, "a?::error::stop.html could not be read")


class CommittedSiteTest(Case):
    """The pages of this repository, so a change that drops a marker fails here before it deploys."""

    # The homepage sast-triage card holds two: its version label and the Action snippet.
    EXPECTED = sorted([("index.html", SAST, "X.Y.Z"), ("index.html", SAST, "X.Y.Z"), ("index.html", SCA, "X.Y.Z"),
                       ("sast-triage.html", SAST, "X.Y"), ("sast-triage.html", SAST, "X.Y"),
                       ("sast-triage.html", SAST, "X.Y.Z")])
    # build_versions.SPOTS lists five of them. The card's Action snippet is marked and filled, but not listed there.
    NOT_IN_SPOTS = [("index.html", SAST, "X.Y.Z")]
    LABEL = re.compile(r'(<([a-z]+)\b[^<>]*\bdata-release="([a-z-]+)" data-release-format="X\.Y(\.Z)?">[^<>0-9]*)'
                       r"[0-9]+(?:\.[0-9]+)+([^<>0-9]*</\2>)")

    def committed(self):
        return {page.relative_to(SITE).as_posix(): page.read_bytes() for page in sorted(SITE.rglob("*.html"))}

    def test_the_six_labels_are_marked_and_each_holds_one_version(self):
        found = []
        for name, content in self.committed().items():
            text, labels, problems, changed = build_versions.fill(name, content.decode("utf-8"), {})
            self.assertEqual(problems, [])
            self.assertEqual((text, changed), (content.decode("utf-8"), 0))
            found += [(name, label.tool, label.shown) for label in labels]
        self.assertEqual(sorted(found), self.EXPECTED)
        self.assertEqual(sorted([(name, tool, shown) for name, tool, shown, count in build_versions.SPOTS
                                 for _ in range(count)] + self.NOT_IN_SPOTS), self.EXPECTED)

    def test_the_committed_versions_are_filled_without_a_change_or_a_warning(self):
        committed, shown = self.committed(), {}
        for tool in (SAST, SCA):
            card = re.search(rf'data-release="{tool}" data-release-format="X\.Y\.Z">[^<>0-9]*([0-9.]+)<',
                             committed["index.html"].decode("utf-8"))
            self.assertIsNotNone(card, f"index.html has no marked {tool} X.Y.Z label")
            shown[tool] = card[1]
        result = run(committed, pulse=pulse_file(shown[SAST]), npm=FakeNpm(shown[SCA]))
        self.assert_filled(result, committed, 0)

    def test_a_release_changes_the_six_labels_and_nothing_else(self):
        committed = self.committed()
        result = run(committed, pulse=pulse_file("98.76.54"), npm=FakeNpm("87.65.43"))

        def version(label):
            numbers = ["98", "76", "54"] if label[3] == SAST else ["87", "65", "43"]
            return label[1] + ".".join(numbers if label[4] else numbers[:2]) + label[5]

        expected, count = {}, 0
        for name, content in committed.items():
            text, replaced = self.LABEL.subn(version, content.decode("utf-8"))
            expected[name], count = text.encode("utf-8"), count + replaced
        self.assertEqual(count, 6)
        self.assert_filled(result, expected, 6)
        for name in ("sast-triage.html", "sca-triage.html"):
            notes = re.findall(rb'<p class="evidence-note">.*?</p>', committed[name], re.S)
            self.assertTrue(notes and all(b"Checked on" in note for note in notes), name)
            self.assertEqual(notes, re.findall(rb'<p class="evidence-note">.*?</p>', result.pages[name], re.S))
        self.assertEqual({name for name in committed if committed[name] != result.pages[name]},
                         {"index.html", "sast-triage.html"})
        self.assertIn(b"lansiquo/sast-triage@v<span", result.pages["sast-triage.html"])
        self.assertIn(b">98.76.54</span></code></pre>", result.pages["sast-triage.html"])


if __name__ == "__main__":
    unittest.main()
