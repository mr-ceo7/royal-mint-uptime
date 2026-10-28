#!/usr/bin/env python3
"""
Checks Royall Mint from outside its server. Run by GitHub Actions every 10 minutes.

A check fails only after three attempts 20 seconds apart. While the site is down, one GitHub issue
labelled `outage` stays open (GitHub notifies the repo owner when it opens); an email goes out through
Resend when the outage starts and when it ends.

Environment: SITE_URL; GITHUB_TOKEN and GITHUB_REPOSITORY (from Actions); optional RESEND_API_KEY,
ALERT_FROM, ALERT_TO.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

ATTEMPTS = 3
PAUSE = 20
LABEL = "outage"


def get(url, timeout=20):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "royal-mint-uptime"}),
                                    timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except OSError as exc:
        return 0, str(exc).encode()


def check_once(site):
    """[] when healthy, else a list of problems."""
    problems = []
    status, _ = get(site + "/")
    if status != 200:
        problems.append(f"Web app (Vercel): {'no answer' if status == 0 else f'HTTP {status}'}")
    status, body = get(site + "/api/health")
    try:
        health = json.loads(body)
    except ValueError:
        health = None
    if status != 200 or not isinstance(health, dict) or health.get("status") != "ok":
        detail = "no answer" if status == 0 else f"HTTP {status}"
        if status and not isinstance(health, dict):
            detail += ", not the API's JSON"
        if isinstance(health, dict):
            down = [k for k in ("database", "redis") if health.get(k) is False]
            if down:
                detail += f", {' and '.join(down)} down"
        problems.append(f"API (home server via tunnel): {detail}")
    elif not (health.get("bot_worker") or {}).get("alive"):
        problems.append("Bot worker: no heartbeat")
    return problems


def check(site):
    for attempt in range(ATTEMPTS):
        problems = check_once(site)
        if not problems:
            return []
        if attempt < ATTEMPTS - 1:
            time.sleep(PAUSE)
    return problems


def github(method, path, body=None):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json",
                 "User-Agent": "royal-mint-uptime"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read() or b"null")


def email(subject, text):
    key, sender, to = (os.environ.get(k, "") for k in ("RESEND_API_KEY", "ALERT_FROM", "ALERT_TO"))
    if not (key and sender and to):
        print("Email not configured; the GitHub issue is the alert.")
        return
    request = urllib.request.Request(
        "https://api.resend.com/emails", method="POST",
        data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": text}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "royal-mint-uptime"})
    try:
        urllib.request.urlopen(request, timeout=20).close()
    except (OSError, urllib.error.HTTPError) as exc:
        print(f"Email failed: {exc}", file=sys.stderr)


def main():
    site = os.environ["SITE_URL"].rstrip("/")
    problems = check(site)
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    open_issues = github("GET", f"/issues?state=open&labels={LABEL}&per_page=1")
    run = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"

    if problems:
        print("DOWN: " + "; ".join(problems))
        text = "\n".join(f"- {p}" for p in problems)
        if open_issues:
            github("POST", f"/issues/{open_issues[0]['number']}/comments", {"body": f"Still down at {now}:\n{text}\n\n{run}"})
        else:
            github("POST", "/issues", {"title": f"Royall Mint is down ({now})", "labels": [LABEL],
                                       "body": f"Seen from GitHub Actions at {now}:\n{text}\n\n{site}\n{run}"})
            email("Royall Mint is down", f"Checked from outside the server at {now}:\n{text}\n\n{site}\n{run}")
        sys.exit(1)

    print("UP")
    if open_issues:
        number = open_issues[0]["number"]
        github("POST", f"/issues/{number}/comments", {"body": f"Back up at {now}.\n\n{run}"})
        github("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": "completed"})
        email("Royall Mint is back up", f"The site answered normally at {now}.\n\n{site}")


if __name__ == "__main__":
    main()
