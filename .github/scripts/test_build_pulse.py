#!/usr/bin/env python3
"""Tests for build_pulse.py. Standard library only. GitHub is never contacted.

Usage: python3 .github/scripts/test_build_pulse.py

FakeGitHub answers the script's requests the way api.github.com does: each
tool's releases come in pages, newest first, with a Link header while more
pages follow. One test starts a web server on this machine instead, to show
that a redirect is not followed.
"""
import contextlib
import email.message
import http.client
import http.server
import io
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
from unittest import mock

sys.dont_write_bytecode = True  # leave no __pycache__ folder in the repository
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_pulse  # noqa: E402

COMMITTED = pathlib.Path(__file__).resolve().parents[2] / "site" / "data" / "pulse.json"
SAST, SCA = "sast-triage", "sca-triage"
TOKEN = "token-that-must-not-be-printed"
WARNING = re.compile(r"warning: release pulse not rebuilt, \S+pulse\.json is unchanged: .+")


def release(tag, published, **fields):
    """One release as the API lists it, cut down to a few fields."""
    return {"tag_name": tag, "published_at": published, "draft": False, "prerelease": False,
            "name": tag, "body": "Release notes.", **fields}


def entry(tool, version, published):
    return {"published": published, "tool": tool, "version": version}


def pulse_file(*entries):
    """The bytes of a pulse.json that holds `entries`."""
    return (json.dumps({"generated": "2026-11-01T00:00:00Z", "releases": list(entries)}, indent=2)
            + "\n").encode()


def headers(**values):
    message = email.message.Message()
    for name, value in values.items():
        message[name.replace("_", "-")] = value
    return message


def http_error(code, **header_values):
    return urllib.error.HTTPError("https://api.github.com/", code, "error",
                                  headers(**header_values), io.BytesIO(b'{"message": "error"}'))


class Answer:
    """A successful answer, as urllib hands it to the script."""

    def __init__(self, body, link=None):
        self.body, self.headers = body, headers(**({"Link": link} if link else {}))

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *error):
        return False


class FakeGitHub:
    """Stands in for api.github.com.

    `releases` maps each tool to the releases GitHub lists for it. `instead`
    maps (tool, page number) to an exception to raise, or to bytes to send, in
    place of that page. Any other address gets HTTP 404. Every request is kept
    in `requests` with the timeout it was made with.
    """

    def __init__(self, releases, instead=None):
        self.releases, self.instead, self.requests = releases, instead or {}, []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        url = urllib.parse.urlsplit(request.full_url)
        found = re.fullmatch(r"/repos/lansiquo/([^/]+)/releases", url.path)
        if (url.scheme, url.netloc) != ("https", "api.github.com") or not found or found[1] not in self.releases:
            raise http_error(404)
        tool, query = found[1], urllib.parse.parse_qs(url.query)
        size, page = int(query["per_page"][0]), int(query["page"][0])
        answer = self.instead.get((tool, page))
        if isinstance(answer, Exception):
            raise answer
        if answer is not None:
            return Answer(answer)
        listed = self.releases[tool]
        base = f"https://api.github.com/repositories/1/releases?per_page={size}&page="
        links = [f'<{base}{page - 1}>; rel="prev"', f'<{base}1>; rel="first"'] if page > 1 else []
        if len(listed) > page * size:
            links += [f'<{base}{page + 1}>; rel="next"', f'<{base}{-(-len(listed) // size)}>; rel="last"']
        return Answer(json.dumps(listed[(page - 1) * size:page * size]).encode(), ", ".join(links))

    def pages_read(self):
        """The (tool, page number) of every request, in order."""
        read = []
        for request, _ in self.requests:
            url = urllib.parse.urlsplit(request.full_url)
            read.append((url.path.split("/")[3], int(urllib.parse.parse_qs(url.query)["page"][0])))
        return read


class Result:
    def __init__(self, code, output, file, names, mode):
        self.code, self.output, self.file, self.names, self.mode = code, output, file, names, mode
        self.data = json.loads(file) if file else None


def run(github, committed=None, env=None, mode=None):
    """Runs the script on a site whose data/pulse.json holds the bytes `committed`.

    `github` answers the requests. With None, the script's own opener is used.
    `mode` sets the file's permission bits before the run.
    GITHUB_TOKEN and GITHUB_ACTIONS are unset unless `env` sets them, so the
    result is the same on a laptop and in CI.
    """
    environment = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GITHUB_ACTIONS")}
    environment.update(env or {})
    opener = mock.patch.object(build_pulse.OPENER, "open", github.open) if github else contextlib.nullcontext()
    with tempfile.TemporaryDirectory() as site:
        target = pathlib.Path(site, "data", "pulse.json")
        target.parent.mkdir()
        if committed is not None:
            target.write_bytes(committed)
            if mode is not None:
                target.chmod(mode)
        out = io.StringIO()
        with opener, mock.patch.object(sys, "argv", ["build_pulse.py", site]), \
                mock.patch.dict(os.environ, environment, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = build_pulse.main()
        file = target.read_bytes() if target.exists() else None
        names = sorted(p.name for p in target.parent.iterdir())
        mode = stat.S_IMODE(target.stat().st_mode) if file is not None else None
    return Result(code, out.getvalue(), file, names, mode)


# Three releases the committed file already holds, and the same three as GitHub lists them.
HELD = pulse_file(entry(SCA, "1.0.0", "2026-11-05T05:23:17Z"), entry(SAST, "1.0.0", "2026-11-05T05:34:39Z"),
                  entry(SAST, "2.0.0", "2026-11-09T18:40:20Z"))
LISTED = {SAST: [release("v2.0.0", "2026-11-09T18:40:20Z"), release("v1.0.0", "2026-11-05T05:34:39Z")],
          SCA: [release("v1.0.0", "2026-11-05T05:23:17Z")]}


class BuildTest(unittest.TestCase):
    def test_writes_the_releases_of_both_tools_sorted_by_published(self):
        github = FakeGitHub({
            SAST: [release("v2.4.1", "2026-11-12T13:17:21Z"), release("v1.0.0", "2026-11-05T05:34:39Z"),
                   release("v0.1.0", "2025-09-21T14:39:18Z")],
            SCA: [release("v1.3.0", "2026-11-12T13:29:15Z"), release("v1.2.4", "2026-11-10T02:02:31Z"),
                  release("v1.0.0", "2026-11-05T05:23:17Z")],
        })
        with mock.patch.object(build_pulse, "utc_now", return_value="2026-11-12T14:00:00Z"):
            result = run(github, committed=HELD)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.file.decode(), """{
  "generated": "2026-11-12T14:00:00Z",
  "releases": [
    {
      "published": "2025-09-21T14:39:18Z",
      "tool": "sast-triage",
      "version": "0.1.0"
    },
    {
      "published": "2026-11-05T05:23:17Z",
      "tool": "sca-triage",
      "version": "1.0.0"
    },
    {
      "published": "2026-11-05T05:34:39Z",
      "tool": "sast-triage",
      "version": "1.0.0"
    },
    {
      "published": "2026-11-10T02:02:31Z",
      "tool": "sca-triage",
      "version": "1.2.4"
    },
    {
      "published": "2026-11-12T13:17:21Z",
      "tool": "sast-triage",
      "version": "2.4.1"
    },
    {
      "published": "2026-11-12T13:29:15Z",
      "tool": "sca-triage",
      "version": "1.3.0"
    }
  ]
}
""")
        self.assertEqual(result.names, ["pulse.json"])
        self.assertRegex(result.output, r"\A\S+pulse\.json: 6 releases \(3 sast-triage, 3 sca-triage\)\n\Z")
        self.assertEqual(github.pages_read(), [(SAST, 1), (SCA, 1)])

    def test_output_is_byte_identical_to_the_committed_file_for_the_same_releases(self):
        committed = COMMITTED.read_bytes()
        data = json.loads(committed)
        self.assertGreater(len(data["releases"]), 0)
        # GitHub lists each tool's releases newest first, with a "v" before the version.
        github = FakeGitHub({tool: [release("v" + r["version"], r["published"])
                                    for r in reversed(data["releases"]) if r["tool"] == tool]
                             for tool in (SAST, SCA)})
        with mock.patch.object(build_pulse, "utc_now", return_value=data["generated"]):
            result = run(github)
        self.assertEqual(result.file, committed)

    def test_generated_is_the_utc_time_of_the_run(self):
        result = run(FakeGitHub(LISTED))
        self.assertRegex(result.data["generated"],
                         r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-6][0-9]Z$")
        self.assertEqual(result.data["releases"], json.loads(HELD)["releases"])

    def test_drafts_prereleases_and_other_tags_are_skipped(self):
        when = "2026-11-12T10:00:00Z"
        skipped = [
            release("v9.0.0", when, draft=True),
            release("v9.0.1", when, prerelease=True),
            release("v9.0.2", when, draft=True, prerelease=True),
            release("v9.0.3", None, draft=True),            # a draft has no published time
            {"tag_name": "v9.0.4", "published_at": when},   # draft and prerelease not stated
            release("v9.0.5", when, draft=None, prerelease=None),
            release("v1", when),                            # the moving major tag
            release("v9.1", when),
            release("9.1.0", when),
            release("V9.1.1", when),
            release("v9.1.2-rc.1", when),
            release("v9.1.3.4", when),
            release("v9.1.4+build", when),
            release("v9.1.5\n", when),
            release("release-v9.1.6", when),
            release("v9.1.٧", when),                   # a digit that is not 0 to 9
            release(None, when),
            release(916, when),
        ]
        github = FakeGitHub({SAST: skipped + LISTED[SAST], SCA: LISTED[SCA]})
        result = run(github, committed=HELD)
        self.assertEqual(result.data["releases"], json.loads(HELD)["releases"])
        self.assertIn("3 releases (2 sast-triage, 1 sca-triage)", result.output)

    def test_values_that_do_not_validate_are_skipped(self):
        bad_times = [None, "", 1762941600, "2026-11-12", "2026-11-12T10:00:00", "2026-11-12T10:00:00+00:00",
                     "2026-11-12T10:00:00.000Z", "2026-11-12 10:00:00Z", "2026-13-01T10:00:00Z",
                     "2026-02-30T10:00:00Z", "2026-11-12T25:00:00Z", "2026-11-12T10:00:00Z\n",
                     "2026-1-2T10:00:00Z", "2026-11-12T10:00:0\u0660Z",  # times that would not sort as text
                     "yesterday", ["2026-11-12T10:00:00Z"]]
        github = FakeGitHub({
            SAST: [release(f"v8.0.{n}", time) for n, time in enumerate(bad_times)]
            + ["v8.1.0", None, 810, ["v8.1.1"]] + LISTED[SAST],
            SCA: LISTED[SCA],
        })
        result = run(github, committed=HELD)
        self.assertEqual(result.data["releases"], json.loads(HELD)["releases"])
        # The tool is one of the two names, whatever a release says about itself.
        ok = release("v1.0.0", "2026-11-05T05:34:39Z")
        self.assertEqual(build_pulse.entry(SAST, ok), entry(SAST, "1.0.0", "2026-11-05T05:34:39Z"))
        self.assertIsNone(build_pulse.entry("other-tool", ok))
        self.assertIsNone(build_pulse.entry("", ok))

    def test_every_page_is_read(self):
        many = [release(f"v3.{n}.0", f"2026-10-{1 + n // 24:02d}T{n % 24:02d}:00:00Z") for n in range(249, -1, -1)]
        github = FakeGitHub({SAST: many, SCA: LISTED[SCA] * 100})
        result = run(github, committed=HELD)
        self.assertEqual(github.pages_read(), [(SAST, 1), (SAST, 2), (SAST, 3), (SCA, 1)])
        self.assertEqual([r["version"] for r in result.data["releases"] if r["tool"] == SAST],
                         [f"3.{n}.0" for n in range(250)])
        self.assertEqual(len(result.data["releases"]), 350)
        for request, timeout in github.requests:
            self.assertRegex(
                request.full_url,
                r"^https://api\.github\.com/repos/lansiquo/(sast|sca)-triage/releases\?per_page=100&page=[1-3]$")
            self.assertEqual(timeout, build_pulse.TIMEOUT)

    def test_releases_published_in_the_same_second_keep_the_order_they_were_read_in(self):
        when = "2026-11-12T10:00:00Z"
        github = FakeGitHub({SAST: [release("v2.0.1", when), release("v2.0.0", when)], SCA: [release("v1.0.0", when)]})
        result = run(github)
        self.assertEqual([(r["tool"], r["version"]) for r in result.data["releases"]],
                         [(SAST, "2.0.1"), (SAST, "2.0.0"), (SCA, "1.0.0")])

    def test_the_same_number_of_releases_or_more_replaces_the_file(self):
        same = run(FakeGitHub(LISTED), committed=HELD)
        self.assertNotEqual(same.file, HELD)
        self.assertEqual(len(same.data["releases"]), 3)
        more = run(FakeGitHub({SAST: [release("v2.0.1", "2026-11-10T00:00:00Z")] + LISTED[SAST], SCA: LISTED[SCA]}),
                   committed=HELD)
        self.assertEqual([r["version"] for r in more.data["releases"]], ["1.0.0", "1.0.0", "2.0.0", "2.0.1"])

    def test_a_missing_or_unreadable_file_is_replaced(self):
        for committed in (None, b"", b"{", b"[]", b'{"releases": 20}'):
            with self.subTest(committed=committed):
                result = run(FakeGitHub(LISTED), committed=committed)
                self.assertEqual(result.data["releases"], json.loads(HELD)["releases"])
                self.assertEqual(result.names, ["pulse.json"])

    def test_the_file_stays_readable_for_the_deploy(self):
        before = os.umask(0o077)
        try:
            result = run(FakeGitHub(LISTED), committed=HELD, mode=0o644)
        finally:
            os.umask(before)
        self.assertEqual(result.mode, 0o644)

    def test_the_token_is_sent_when_set_and_never_printed(self):
        github = FakeGitHub(LISTED)
        result = run(github, committed=HELD, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual([request.get_header("Authorization") for request, _ in github.requests],
                         [f"Bearer {TOKEN}"] * 2)
        self.assertNotIn(TOKEN, result.output)
        self.assertNotIn(TOKEN.encode(), result.file)
        for token in (None, ""):
            github = FakeGitHub(LISTED)
            run(github, committed=HELD, env={} if token is None else {"GITHUB_TOKEN": token})
            self.assertEqual([request.get_header("Authorization") for request, _ in github.requests], [None] * 2)


class FailureTest(unittest.TestCase):
    """Whatever goes wrong, the file stays as committed and the deploy goes on."""

    def assert_untouched(self, result, reason):
        self.assertEqual(result.code, 0)
        self.assertEqual(result.file, HELD)
        self.assertEqual(result.names, ["pulse.json"])
        self.assertEqual(len(result.output.splitlines()), 1, result.output)
        self.assertRegex(result.output, WARNING)
        self.assertIn(reason, result.output)
        self.assertNotIn(TOKEN, result.output)

    def test_a_failed_request_keeps_the_file(self):
        unreachable = "GitHub could not be reached for {tool}"
        not_json = "GitHub's answer for {tool} is not valid JSON"
        not_a_list = "GitHub's answer for {tool} is not a list of releases"
        failures = {
            "network down": (urllib.error.URLError(OSError(101, "Network is unreachable")), unreachable),
            "name not found": (urllib.error.URLError(OSError(-2, "Name or service not known")), unreachable),
            "timeout": (TimeoutError("timed out"), unreachable),
            "connection reset": (ConnectionResetError(104, "Connection reset by peer"), unreachable),
            "answer cut short": (http.client.IncompleteRead(b'[{"tag_name"'), unreachable),
            "HTTP 500": (http_error(500), "GitHub answered HTTP 500 for {tool}"),
            "HTTP 502": (http_error(502), "GitHub answered HTTP 502 for {tool}"),
            "HTTP 404": (http_error(404), "GitHub answered HTTP 404 for {tool}"),
            "HTTP 401": (http_error(401), "GitHub answered HTTP 401 for {tool}"),
            "HTTP 403": (http_error(403, X_RateLimit_Remaining="57"), "GitHub answered HTTP 403 for {tool}"),
            "HTTP 301": (http_error(301, Location="https://example.com/"), "GitHub answered HTTP 301 for {tool}"),
            "rate limit, HTTP 403": (http_error(403, X_RateLimit_Remaining="0"),
                                     "GitHub answered HTTP 403 for {tool} (rate limit reached)"),
            "rate limit, HTTP 429": (http_error(429, Retry_After="60"),
                                     "GitHub answered HTTP 429 for {tool} (rate limit reached)"),
            "invalid JSON": (b"<html>Bad gateway</html>", not_json),
            "JSON cut short": (b'[{"tag_name": "v9.9.9", "published_at"', not_json),
            "empty answer": (b"", not_json),
            "not UTF-8": (b"\xff\xfe[]", not_json),
            "JSON object": (b'{"message": "Not Found"}', not_a_list),
            "JSON null": (b"null", not_a_list),
            # The text of an unexpected error is never printed: it could quote the token.
            "unexpected error": (RuntimeError(f"Invalid header value b'Bearer {TOKEN}'"), "unexpected RuntimeError"),
        }
        for name, (failure, reason) in failures.items():
            for tool in (SAST, SCA):
                with self.subTest(failure=name, tool=tool):
                    github = FakeGitHub(LISTED, {(tool, 1): failure})
                    result = run(github, committed=HELD, env={"GITHUB_TOKEN": TOKEN})
                    self.assert_untouched(result, reason.format(tool=tool))
                    self.assertEqual(github.pages_read(), [(SAST, 1)] if tool == SAST else [(SAST, 1), (SCA, 1)])
        self.assertNotIn("rate limit", run(FakeGitHub(LISTED, {(SAST, 1): http_error(403)}), committed=HELD).output)

    def test_a_failure_on_a_later_page_keeps_the_file(self):
        many = [release(f"v3.{n}.0", f"2026-10-{1 + n // 24:02d}T{n % 24:02d}:00:00Z") for n in range(250)]
        for failure, reason in ((http_error(503), "GitHub answered HTTP 503 for sast-triage"),
                                (b"[", "GitHub's answer for sast-triage is not valid JSON"),
                                (urllib.error.URLError(TimeoutError("timed out")),
                                 "GitHub could not be reached for sast-triage")):
            with self.subTest(reason=reason):
                github = FakeGitHub({SAST: many, SCA: LISTED[SCA]}, {(SAST, 3): failure})
                self.assert_untouched(run(github, committed=HELD), reason)
                self.assertEqual(github.pages_read(), [(SAST, 1), (SAST, 2), (SAST, 3)])

    def test_pages_without_end_keep_the_file(self):
        many = [release(f"v3.{n}.0", "2026-10-01T00:00:00Z") for n in range(1000)]
        github = FakeGitHub({SAST: many, SCA: LISTED[SCA]})
        with mock.patch.object(build_pulse, "MAX_PAGES", 4):
            self.assert_untouched(run(github, committed=HELD), "more than 4 pages of releases for sast-triage")
        self.assertEqual(github.pages_read(), [(SAST, 1), (SAST, 2), (SAST, 3), (SAST, 4)])

    def test_zero_releases_keep_the_file(self):
        when = "2026-11-12T10:00:00Z"
        nothing = {
            "no releases": {SAST: [], SCA: []},
            "only drafts and prereleases": {SAST: [release("v9.0.0", when, draft=True)],
                                            SCA: [release("v9.0.0", when, prerelease=True)]},
            "only other tags": {SAST: [release("v1", when)], SCA: [release("nightly", when)]},
        }
        for name, listed in nothing.items():
            with self.subTest(listed=name):
                self.assert_untouched(run(FakeGitHub(listed), committed=HELD), "no published vX.Y.Z release")
        # With no file to keep, none is written.
        result = run(FakeGitHub({SAST: [], SCA: []}))
        self.assertEqual((result.code, result.file, result.names), (0, None, []))
        self.assertRegex(result.output, WARNING)

    def test_fewer_releases_than_the_file_holds_keep_the_file(self):
        fewer = {
            "one tool lists nothing": {SAST: LISTED[SAST], SCA: []},
            "a release is gone": {SAST: LISTED[SAST][:1], SCA: LISTED[SCA]},
            "a release became a draft": {SAST: [release("v2.0.0", "2026-11-09T18:40:20Z", draft=True),
                                                LISTED[SAST][1]], SCA: LISTED[SCA]},
        }
        for name, listed in fewer.items():
            with self.subTest(listed=name):
                self.assert_untouched(run(FakeGitHub(listed), committed=HELD),
                                      "GitHub listed 2 releases, fewer than the 3 in the file")

    def test_a_failed_write_keeps_the_file(self):
        for step in ("open", "replace"):
            with self.subTest(step=step):
                # `open` is patched in the script only, so the test can still read the file.
                where, error = ((build_pulse, PermissionError(13, "Permission denied")) if step == "open" else
                                (build_pulse.os, OSError(28, "No space left on device")))
                with mock.patch.object(where, step, side_effect=error, create=True):
                    result = run(FakeGitHub(LISTED), committed=HELD)
                self.assert_untouched(result, "could not be written")

    def test_in_github_actions_the_warning_is_an_annotation(self):
        result = run(FakeGitHub(LISTED, {(SAST, 1): http_error(500)}), committed=HELD, env={"GITHUB_ACTIONS": "true"})
        self.assertEqual((result.code, result.file), (0, HELD))
        self.assertRegex(result.output, r"\A::warning::release pulse not rebuilt, \S+pulse\.json is unchanged: "
                                        r"GitHub answered HTTP 500 for sast-triage\n\Z")


class RedirectTest(unittest.TestCase):
    def test_a_redirect_is_not_followed_so_the_token_goes_nowhere_else(self):
        seen = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append((self.path, self.headers.get("Authorization")))
                body = json.dumps(LISTED[SAST] * 5).encode() if self.path == "/elsewhere" else b""
                self.send_response(200 if body else 302)
                if not body:
                    self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/elsewhere")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with mock.patch.object(build_pulse, "API", f"http://127.0.0.1:{server.server_port}"):
                result = run(None, committed=HELD, env={"GITHUB_TOKEN": TOKEN, "no_proxy": "127.0.0.1"})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)
        self.assertEqual(seen, [("/repos/lansiquo/sast-triage/releases?per_page=100&page=1", f"Bearer {TOKEN}")])
        self.assertEqual((result.code, result.file), (0, HELD))
        self.assertRegex(result.output, WARNING)
        self.assertIn("GitHub answered HTTP 302 for sast-triage", result.output)


if __name__ == "__main__":
    unittest.main()
