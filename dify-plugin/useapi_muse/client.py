"""HTTP client for the useapi.net Muse API.

Every request goes to https://api.useapi.net/v1/muse with the user's useapi.net
API token as a Bearer token. Finished files are downloaded from the same API
(GET /assets/{assetId}), which streams them from the Muse account's workspace.
Nothing else is contacted.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import requests

BASE_URL = "https://api.useapi.net/v1/muse"
USER_AGENT = "dify-plugin-muse-useapi/0.1.0"

SETUP_TOKEN_URL = "https://useapi.net/docs/start-here/setup-useapi"
SETUP_ACCOUNT_URL = "https://useapi.net/docs/start-here/setup-muse"
SUBSCRIPTION_URL = "https://useapi.net/docs/subscription"

# Seconds.
DEFAULT_TIMEOUT = 60
ACCOUNT_TIMEOUT = 90  # GET /accounts/{email} reads the plan live from Muse
SUBMIT_TIMEOUT = 120  # async job submission answers at once; a re-sign-in can add time
CHAT_TIMEOUT = 150  # sending a chat message waits until Muse accepted it
UPLOAD_TIMEOUT = 300  # Muse takes files at about 1 MB per second, 50 MB at most
DOWNLOAD_TIMEOUT = 300


class UseapiError(Exception):
    """A readable error for the Dify user or agent."""

    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class FileTooLarge(Exception):
    def __init__(self, size: int):
        super().__init__(size)
        self.size = size


def enc(value: str) -> str:
    """URL-encode an id or email for use in a path. Ids contain ':' and '@'."""
    return quote(str(value), safe="")


def _server_message(body: Any) -> str:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):  # a failed job record: {code, message}
            msg = err.get("message") or ""
            return str(msg)
        if err:
            return str(err)
    if isinstance(body, str):
        return body.strip()[:500]
    return ""


def _retry_after(body: Any, headers: Any) -> str:
    seconds = None
    if headers is not None:
        try:
            seconds = headers.get("Retry-After")
        except AttributeError:
            seconds = None
    if seconds:
        return f" Retry after {seconds} seconds."
    if isinstance(body, dict):
        err = body.get("error")
        when = body.get("retryAt") or (err.get("retryAt") if isinstance(err, dict) else None)
        if when:
            return f" Retry after {when}."
    return ""


def describe_error(status: int, body: Any, headers: Any = None) -> str:
    """Turn an HTTP error from the API into one or two readable sentences.

    Meanings follow the published API catalog (https://api.useapi.net/v1/muse/models, `errors`)
    and the Muse API reference (https://useapi.net/docs/api-muse-v1).
    """
    server = _server_message(body)
    low = server.lower()
    detail = f" Details: {server}" if server else ""
    later = _retry_after(body, headers)

    if status == 401:
        return f"useapi.net rejected the API token (401 Unauthorized). Check the token in the plugin's credentials. How to get one: {SETUP_TOKEN_URL}"
    if status == 402:
        return f"Your useapi.net subscription is not active (402 Payment Required). See {SUBSCRIPTION_URL}.{detail}"
    if status == 400:
        if "configure at least one account" in low:
            return f"No Muse account is connected to useapi.net yet (400). Add one first: {SETUP_ACCOUNT_URL}"
        if "was not provided" in low:
            return f"The prompt names an input (image_N, video_N or audio_N) that was not given (400). Give it, or remove the name from the prompt.{detail}"
        return f"The request was refused (400). Change what the details say and try again.{detail}"
    if status == 403:
        if "does not belong to this api token" in low:
            return f"That id belongs to another useapi.net API token (403). Use ids made with this token.{detail}"
        if "keeps refusing this prompt on every account" in low:
            return (
                "Muse keeps refusing this prompt on every account that could take it, so it was not sent and nothing was made (403). "
                f"Change the prompt.{detail}"
            )
        if "keeps refusing this prompt" in low:
            return (
                "Muse keeps refusing this prompt on that account, so it was not sent and nothing was made (403). "
                f"Change the prompt, or run it on another Muse account.{detail}"
            )
        if "switched off video for all" in low:
            return (
                "Meta has switched off video for every connected Muse account in its country or region (403). Image jobs still work. "
                f"Connect an account where video works.{detail}"
            )
        if "switched off video" in low:
            return (
                "Meta has switched off video for this Muse account in its country or region (403). Image jobs still work on it. "
                f"Run videos on another account, or leave the email empty.{detail}"
            )
        return f"Muse refused this request (403). Sending the same prompt again will not help: change the prompt or the inputs.{detail}"
    if status == 404:
        if "not configured" in low:
            return f"That Muse account is not connected to useapi.net (404). Connect it first: {SETUP_ACCOUNT_URL}{detail}"
        return f"Not found (404).{detail}"
    if status == 409:
        if "no longer waiting" in low:
            return f"This permission request was already answered or has ended (409).{detail}"
        return (
            "Muse says this account already made this request or already has it queued, so nothing was made (409). "
            f"Change the prompt, or run it on another Muse account.{detail}"
        )
    if status == 410:
        return "The job has expired (410). Job records are kept for 7 days."
    if status == 411:
        return f"The file was sent without its size (411). Try the upload again.{detail}"
    if status == 412:
        return (
            "The weekly Muse allowance is used up (412) on this account, or on every account when no email is set. "
            f"It counts again after the reset time: 'Get Muse account usage' shows it. Or connect another Muse account.{detail}"
        )
    if status == 413:
        return "The file is larger than 50 MB (413). Muse accepts files up to 50 MB."
    if status == 422:
        return f"Muse could not do this with the item (422).{detail}"
    if status == 429:
        if "video limit" in low and low.startswith("all "):
            return (
                f"Every connected Muse account reached Muse's video limit for the last 24 hours (429), so nothing was made.{later} "
                f"Image jobs still work.{detail}"
            )
        if "video limit" in low:
            return (
                f"The Muse account reached Muse's video limit for the last 24 hours (429), so nothing was made.{later} "
                f"Image jobs still work. Run the video on another account, or leave the email empty.{detail}"
            )
        if "maxjobs" in low or "maximum number of jobs" in low:
            return f"Every job slot (maxJobs) of the Muse account is busy (429).{later or ' Retry in about 30 seconds.'}{detail}"
        return f"Muse is limiting requests on the account right now (429).{later or ' Retry in about a minute.'}{detail}"
    if status == 502:
        return (
            "Muse answered with an error (502). If this was a generation, Muse may have made the file anyway: "
            f"check 'Get job status' before running it again, since a new run uses the allowance again.{detail}"
        )
    if status == 503:
        return f"Muse could not be reached or could not do it right now (503).{later or ' Retry shortly.'}{detail}"
    if status == 504:
        return f"The connection to Muse dropped or Muse did not finish in time (504). It may still have run: check before sending it again.{detail}"
    if status == 596:
        if "no healthy" in low:
            return f"No connected Muse account is healthy (596). Check 'List Muse accounts' and add the account again: {SETUP_ACCOUNT_URL}{detail}"
        return (
            "The Muse account needs attention and is paused (596): Meta asks for a security check, Muse refused to sign it in again, "
            "or Muse took its computer away. Sign in at https://muse.ai in a browser to see what it needs, and do what the details say "
            f"before you add the account again: {SETUP_ACCOUNT_URL}{detail}"
        )
    if status >= 500:
        return f"Something failed on the useapi.net side ({status}). Retry in a minute.{detail}"
    return f"Request failed ({status}).{detail}"


def _parse_body(resp: requests.Response) -> Any:
    text = resp.text
    if not text:
        return None
    try:
        return resp.json()
    except ValueError:
        return text


_FILENAME_RE = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", re.IGNORECASE)


def filename_from(disposition: str | None) -> str | None:
    """The file name of a Content-Disposition header, without any path."""
    if not disposition:
        return None
    match = _FILENAME_RE.search(disposition)
    if not match:
        return None
    name = match.group(1).strip().replace("\\", "/").rsplit("/", 1)[-1]
    return name or None


class Client:
    def __init__(self, token: str, session: requests.Session | None = None, base_url: str = BASE_URL):
        token = (token or "").strip()
        if not token:
            raise UseapiError(f"The useapi.net API token is missing. How to get one: {SETUP_TOKEN_URL}")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.http = session or requests.Session()

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if extra:
            headers.update(extra)
        return headers

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Any:
        """Send one request and return the parsed JSON body, or raise UseapiError."""
        extra: dict[str, str] = {}
        payload: bytes | None = None
        if body is not None:
            extra["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")
        elif data is not None:
            extra["Content-Type"] = content_type or "application/octet-stream"
            payload = data
        clean_params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        try:
            resp = self.http.request(
                method,
                self.url(path),
                params=clean_params or None,
                data=payload,
                headers=self._headers(extra),
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.Timeout as e:
            raise UseapiError(
                f"No answer from api.useapi.net within {int(timeout)} seconds. "
                "The request may still complete: check 'List running jobs' or the chat before retrying anything that generates."
            ) from e
        except requests.RequestException as e:
            raise UseapiError(f"Could not reach api.useapi.net: {e.__class__.__name__}") from e

        parsed = _parse_body(resp)
        if resp.status_code < 300:
            return parsed if parsed is not None else {}
        raise UseapiError(describe_error(resp.status_code, parsed, resp.headers), resp.status_code, parsed)

    def download_asset(
        self,
        asset_id: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = DOWNLOAD_TIMEOUT,
        max_bytes: int | None = None,
        budget: float | None = None,
    ) -> tuple[bytes, str, str | None]:
        """Download a file with GET /assets/{assetId}. Returns (bytes, content type, file name).

        The API streams the file from the account's Muse workspace; nothing is fetched from another host.
        """
        end = None if budget is None else time.monotonic() + budget  # total-time limit; the read timeout is per read
        if budget is not None:
            timeout = max(1.0, min(timeout, budget))
        clean_params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        try:
            resp = self.http.request(
                "GET",
                self.url(f"assets/{enc(asset_id)}"),
                params=clean_params or None,
                headers=self._headers({"Accept": "*/*"}),
                timeout=timeout,
                stream=True,
                allow_redirects=False,
            )
        except requests.Timeout as e:
            raise UseapiError(f"The file download did not finish within {int(timeout)} seconds.") from e
        except requests.RequestException as e:
            raise UseapiError(f"Could not reach api.useapi.net: {e.__class__.__name__}") from e
        if resp.status_code >= 300:
            parsed = _parse_body(resp)
            resp.close()
            raise UseapiError(describe_error(resp.status_code, parsed, resp.headers), resp.status_code, parsed)
        length = resp.headers.get("Content-Length")
        if max_bytes and length and length.isdigit() and int(length) > max_bytes:
            resp.close()
            raise FileTooLarge(int(length))
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if end is not None and time.monotonic() > end:
                resp.close()
                raise UseapiError("The file download ran out of time.")
            total += len(chunk)
            if max_bytes and total > max_bytes:
                resp.close()
                raise FileTooLarge(total)
            chunks.append(chunk)
        content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0].strip()
        return b"".join(chunks), content_type, filename_from(resp.headers.get("Content-Disposition"))
