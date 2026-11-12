#!/usr/bin/env python3
"""Builds the release pulse data before the site deploys. Standard library only.

Usage: python3 .github/scripts/build_pulse.py [site_dir]

Reads the releases of sast-triage and sca-triage from the GitHub REST API and
writes <site_dir>/data/pulse.json, the file site/pulse.js draws the header
pulse from. It keeps the published releases that are not drafts or
prereleases and whose tag is exactly vX.Y.Z, oldest first:

    {"generated": "<UTC time of this run>",
     "releases": [{"published": "<UTC time>", "tool": "<name>", "version": "X.Y.Z"}]}

A release whose tag, state or published time is anything else is skipped.
Requests carry GITHUB_TOKEN from the environment when it is set, which raises
GitHub's rate limit. Without it they are anonymous.

A deploy must never break and never show fewer releases than the committed
file. So on any failure (GitHub cannot be reached, an HTTP error, the rate
limit, an answer that is not the expected JSON, no releases, or fewer releases
than the file already holds) the file is left untouched, one warning line is
printed and the exit code is still 0. A file that is missing or cannot be read
holds no releases, so it is replaced.
"""
import datetime
import http.client
import json
import os
import pathlib
import re
import shutil
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
OWNER = "lansiquo"
TOOLS = ("sast-triage", "sca-triage")
TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
PER_PAGE = 100
# A tool with more pages than this is treated as a failure, not cut short.
MAX_PAGES = 50
TIMEOUT = 10  # seconds, for each request


class Unavailable(Exception):
    """Why the pulse data cannot be rebuilt on this run."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turns a redirect into an HTTP error, so the token is sent to GitHub's API and nowhere else."""

    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(TIME_FORMAT)


def entry(tool, release):
    """Returns the pulse entry for one release from the API, or None to skip it.

    Every value is checked here: the tool is one of TOOLS, the tag is exactly
    vX.Y.Z, and the published time is a real UTC time written the way GitHub
    writes it, so sorting the text sorts the times.
    """
    if tool not in TOOLS or not isinstance(release, dict):
        return None
    if release.get("draft") is not False or release.get("prerelease") is not False:
        return None
    tag, published = release.get("tag_name"), release.get("published_at")
    if not isinstance(tag, str) or not TAG.fullmatch(tag):
        return None
    if not isinstance(published, str) or not TIME.fullmatch(published):
        return None
    try:
        datetime.datetime.strptime(published, TIME_FORMAT)
    except ValueError:
        return None
    return {"published": published, "tool": tool, "version": tag[1:]}


def page(tool, number, token):
    """Fetches one page of a tool's releases.

    Returns the list GitHub sent and whether another page follows.
    """
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "dotrobin-dev-build-pulse"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{API}/repos/{OWNER}/{tool}/releases?per_page={PER_PAGE}&page={number}", headers=headers)
    try:
        with OPENER.open(request, timeout=TIMEOUT) as response:
            body, link = response.read(), response.headers.get("Link") or ""
    except urllib.error.HTTPError as error:
        limited = error.code == 429 or (error.headers or {}).get("X-RateLimit-Remaining") == "0"
        error.close()
        raise Unavailable(f"GitHub answered HTTP {error.code} for {tool}"
                          + (" (rate limit reached)" if limited else "")) from None
    except (OSError, http.client.HTTPException) as error:
        raise Unavailable(f"GitHub could not be reached for {tool} ({type(error).__name__})") from None
    try:
        listed = json.loads(body)
    except ValueError:
        raise Unavailable(f"GitHub's answer for {tool} is not valid JSON") from None
    if not isinstance(listed, list):
        raise Unavailable(f"GitHub's answer for {tool} is not a list of releases")
    return listed, 'rel="next"' in link


def published_releases(token):
    """Returns the pulse entries of both tools, oldest first."""
    entries = []
    for tool in TOOLS:
        for number in range(1, MAX_PAGES + 1):
            listed, more = page(tool, number, token)
            entries += filter(None, (entry(tool, release) for release in listed))
            if not more:
                break
        else:
            raise Unavailable(f"GitHub has more than {MAX_PAGES} pages of releases for {tool}")
    return sorted(entries, key=lambda e: e["published"])


def held(target):
    """How many releases the file already holds: 0 if it is missing or cannot be read."""
    try:
        releases = json.loads(target.read_bytes())["releases"]
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    return len(releases) if isinstance(releases, list) else 0


def write(target, data):
    """Replaces the file in one step, so a write that fails leaves the old file whole."""
    draft = target.with_name(target.name + ".tmp")
    try:
        with open(draft, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, indent=2) + "\n")
        if target.exists():
            shutil.copymode(target, draft)  # Pages only serves a file that everyone may read
        os.replace(draft, target)
    except OSError as error:
        raise Unavailable(f"the file could not be written ({type(error).__name__})") from None
    finally:
        draft.unlink(missing_ok=True)


def main():
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    target = site / "data" / "pulse.json"
    try:
        releases = published_releases(os.environ.get("GITHUB_TOKEN"))
        before = held(target)
        if not releases:
            raise Unavailable("GitHub listed no published vX.Y.Z release")
        if len(releases) < before:
            raise Unavailable(f"GitHub listed {len(releases)} releases, fewer than the {before} in the file")
        write(target, {"generated": utc_now(), "releases": releases})
    except Exception as error:  # whatever went wrong, the deploy goes on with the committed file
        # Only the kind of an unexpected error is printed: its text could quote a request header.
        reason = str(error) if isinstance(error, Unavailable) else f"unexpected {type(error).__name__}"
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "warning: "
        print(f"{prefix}release pulse not rebuilt, {target} is unchanged: {reason}")
        return 0
    counts = ", ".join(f"{sum(r['tool'] == tool for r in releases)} {tool}" for tool in TOOLS)
    print(f"{target}: {len(releases)} releases ({counts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
