#!/usr/bin/env python3
import argparse
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_VERSION = "2026-03-10"


def api_request(url, token, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "ato-ippai-last-train-ops",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            data = json.loads(text) if text else None
            return response.status, data
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API {error.code} {method} {url}: {detail}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed {method} {url}: {error}") from error


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch a workflow_dispatch verifier and fail unless it completes successfully."
    )
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--ref", default="main")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-minutes", type=int, default=20)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository:
        parser.error("GITHUB_REPOSITORY is required")
    if not token:
        parser.error("GITHUB_TOKEN is required")

    workflow_id = quote(args.workflow, safe="")
    dispatch_url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_id}/dispatches"
    )

    status, dispatched = api_request(
        dispatch_url,
        token,
        method="POST",
        payload={"ref": args.ref, "return_run_details": True},
    )

    if status != 200 or not isinstance(dispatched, dict):
        raise RuntimeError(
            f"Workflow dispatch did not return run details: status={status} body={dispatched}"
        )

    run_id = dispatched.get("workflow_run_id")
    run_url = dispatched.get("run_url")
    html_url = dispatched.get("html_url")
    if not run_id or not run_url:
        raise RuntimeError(f"Workflow dispatch response is incomplete: {dispatched}")

    print(
        f"::notice title=Verifier dispatched::{args.workflow} "
        f"run={run_id} {html_url or run_url}"
    )

    deadline = time.monotonic() + args.timeout_minutes * 60
    last_status = None

    while time.monotonic() < deadline:
        _, run = api_request(run_url, token)
        current_status = run.get("status")
        conclusion = run.get("conclusion")

        if current_status != last_status:
            print(
                f"Verifier {args.workflow} run={run_id} status={current_status} "
                f"conclusion={conclusion}"
            )
            last_status = current_status

        if current_status == "completed":
            if conclusion == "success":
                print(f"::notice title=Verifier passed::{args.workflow} run={run_id}")
                return 0

            print(
                f"::error title=Verifier failed::{args.workflow} run={run_id} "
                f"conclusion={conclusion} url={html_url or run_url}"
            )
            return 1

        time.sleep(args.poll_seconds)

    print(
        f"::error title=Verifier timed out::{args.workflow} run={run_id} "
        f"after {args.timeout_minutes} minutes url={html_url or run_url}"
    )
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"::error title=Verifier orchestration error::{error}")
        raise
