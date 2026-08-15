#!/usr/bin/env -S uv run
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///
"""Webhook trigger — FastAPI endpoint that launches runs from GitHub events.

Responds 200 immediately (the shared core launches the slice detached) to beat
GitHub's ~10s webhook timeout. Deps are declared inline (PEP 723) so the main
project stays dependency-free.

Usage: uv run triggers/trigger_webhook.py   (PORT env var, default 8001)
"""

import os
import sys

import uvicorn
from fastapi import FastAPI, Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import trigger

app = FastAPI(title="ADW Webhook Trigger")


@app.post("/gh-webhook")
async def gh_webhook(request: Request):
    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()
    action = payload.get("action", "")
    issue = payload.get("issue", {})
    number = issue.get("number")

    # Pull the body to inspect: the issue body on open, the comment on comment.
    body = ""
    if event == "issues" and action == "opened":
        body = issue.get("body", "")
    elif event == "issue_comment" and action == "created":
        body = payload.get("comment", {}).get("body", "")

    adw_id = trigger.handle_issue(str(number), body) if number else None
    if adw_id:
        return {"status": "accepted", "issue": number, "adw_id": adw_id}
    return {"status": "ignored"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
