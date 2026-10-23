"""One authenticated sync, strict readback validation, no mutation retries."""
import json
import os
import re
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://mrcolombo-otto-sync.d0minik88.chatgpt.site/api/sync"
EXPECTED = {
    "catalog": 68, "resolved": 68, "quarantined": 0,
    "ottoSkusMissing": 0, "ottoReadbackMismatches": 0,
    "deliveryMappingsMissingAfter": 0, "activeSkus": 68,
    "marketplaceRows": 68, "unresolvedLedgerAfter": 0,
    "mode": "LIVE_FULL", "orderMirror": "ON",
}


def safe_summary(body):
    """Never log raw HTTP bodies, upstream messages, credentials or order data."""
    if not isinstance(body, dict):
        return {"reason": "INVALID_RESPONSE"}
    result = {}
    run_id = body.get("runId")
    if isinstance(run_id, str) and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", run_id):
        result["runId"] = run_id
    status = body.get("status")
    result["status"] = status if status in ("SUCCEEDED", "FAILED", "SKIPPED") else "INVALID"
    counters = body.get("counters")
    if isinstance(counters, dict):
        result["counters"] = {
            key: value for key, value in counters.items()
            if key in EXPECTED and (
                type(value) is int or (key in ("mode", "orderMirror") and value in ("LIVE_FULL", "DRY_RUN", "OFF", "ON", "DRAIN", "OTTO_ZERO", "LIVE_OTTO"))
            )
        }
    error = body.get("error", "")
    if isinstance(error, str):
        if error.startswith("OTTO-Mengen-Readback weicht bei "):
            result["reason"] = "OTTO_QUANTITY_READBACK_MISMATCH"
        elif error.startswith("OTTO-Versandprofil-Readback weicht bei "):
            result["reason"] = "OTTO_DELIVERY_READBACK_MISMATCH"
        elif error:
            result["reason"] = "SYNC_FAILED_CHECK_PRIVATE_RUN_LOG"
    return result


def valid(body):
    if not isinstance(body, dict) or body.get("status") != "SUCCEEDED":
        return False
    counters = body.get("counters")
    return isinstance(counters, dict) and all(
        type(counters.get(key)) is type(value) and counters[key] == value
        for key, value in EXPECTED.items()
    )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward authentication to a redirect target.


def main(opener=None, environ=None):
    environ = os.environ if environ is None else environ
    bearer = environ.get("OAI_SITES_AUTHORIZATION", "").strip()
    key = environ.get("SYNC_API_KEY", "").strip()
    if not bearer or not key:
        print("::error::Sync credentials are missing")
        return 1
    request = urllib.request.Request(ENDPOINT, method="POST", data=b"{}", headers={
        "OAI-Sites-Authorization": "Bearer " + bearer,
        "x-sync-key": key, "content-type": "application/json",
    })
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        response = opener(request, timeout=240)
    except urllib.error.HTTPError as error:
        response = error  # Read bounded JSON even on non-2xx; never replay POST.
    except (OSError, TimeoutError, urllib.error.URLError):
        print("::error::Sync transport failed or timed out; outcome is unconfirmed. No automatic POST retry.")
        return 1
    try:
        with response:
            status = response.code
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("Response too large")
        body = json.loads(raw)
    except (ValueError, OSError, TimeoutError):
        print("::error::Sync returned an invalid or unreadable response; inspect private service logs")
        return 1
    summary = json.dumps(safe_summary(body), ensure_ascii=True, separators=(",", ":"))
    if not 200 <= status < 300 or not valid(body):
        print(f"::error::OTTO sync failed (HTTP {status}): {summary}")
        return 1
    print("OTTO sync succeeded: " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
