"""One handler per Dify tool. Each handler yields Out items that runner.py turns
into Dify messages, so the handlers can be unit-tested without Dify.

API reference: https://useapi.net/docs/api-muse-v1
API catalog (inputs, limits, errors): https://api.useapi.net/v1/muse/models
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from . import params as P
from .client import (
    ACCOUNT_TIMEOUT,
    CHAT_TIMEOUT,
    SETUP_ACCOUNT_URL,
    SUBMIT_TIMEOUT,
    UPLOAD_TIMEOUT,
    Client,
    FileTooLarge,
    UseapiError,
    enc,
)

POLL_SECONDS = 10
DEFAULT_WAIT = 120  # agent friendly: a Dify agent turn stays short
VIDEO_WAIT = 180  # a Muse video took 60 to 140 seconds in useapi.net's tests
MAX_WAIT = 420  # leaves room for file downloads under Dify's default 600 s plugin execution limit
DOWNLOAD_DEADLINE = 570  # seconds from the tool's start: no file download begins or runs past this
MAX_FILE_BYTES = 150 * 1024 * 1024
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # POST /assets: 52,428,800 bytes
MAX_PROMPT = 5000
CHAT_PAGE = 200  # GET /chats/{chatId} limit: events (messages and files) per read

# POST /assets Content-Type values (catalog `assets-upload`), with the input kind each one is.
UPLOAD_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/webm": "video",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/mp4": "audio",
    "audio/x-m4a": "audio",
    "audio/ogg": "audio",
}
MIME_ALIASES = {"image/jpg": "image/jpeg", "audio/mp3": "audio/mpeg", "audio/wave": "audio/wav", "audio/m4a": "audio/x-m4a"}
EXT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/x-m4a",
    "ogg": "audio/ogg",
}
FILE_EXT = {
    "image/webp": "webp",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "application/pdf": "pdf",
    "text/markdown": "md",
    "text/plain": "txt",
    "text/csv": "csv",
    "text/html": "html",
}

PLAN_NAMES = {"HATCH_FREE": "Free"}  # GET /accounts quota.tier; other tiers are shown as Muse names them
CHAT_BUSY = ("running", "pending_user_confirmation", "queued", "started")

SECRET_KEYS = ("password", "cookies", "session_token", "accessToken")
BULKY_KEYS = ("html", "history")


@dataclass
class Out:
    kind: str  # text | json | var | blob | link
    value: Any
    name: str | None = None
    meta: dict[str, Any] | None = None


def text(value: str) -> Out:
    return Out("text", value)


def js(value: Any) -> Out:
    return Out("json", value if isinstance(value, (dict, list)) else {"result": value})


def var(name: str, value: Any) -> Out:
    return Out("var", value, name=name)


@dataclass
class Ctx:
    client: Client
    default_email: str | None = None
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    t0: float = field(init=False, default=0.0)  # the tool's start, for the overall download deadline

    def __post_init__(self) -> None:
        self.t0 = self.clock()

    def download_budget(self) -> float:
        """Seconds left before files must stop being attached."""
        return self.t0 + DOWNLOAD_DEADLINE - self.clock()

    def email(self, p: dict[str, Any]) -> str | None:
        """The tool's email, else the credentials' default, else None (useapi.net then picks an account)."""
        return P.text(p, "email") or self.default_email

    def get(self, path: str, **kw: Any) -> Any:
        return self.client.request("GET", path, **kw)

    def post(self, path: str, body: dict[str, Any], **kw: Any) -> Any:
        return self.client.request("POST", path, body=body, **kw)


Handler = Callable[[Ctx, dict[str, Any]], Iterator[Out]]
HANDLERS: dict[str, Handler] = {}


def tool(name: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[name] = fn
        return fn

    return register


def done(message: str, data: Any) -> Iterator[Out]:
    yield text(message)
    yield js(data)


def slim(value: Any) -> Any:
    """A copy for the JSON output without widget HTML, raw chat history or anything secret-looking."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in SECRET_KEYS:
                continue
            if k in BULKY_KEYS:
                if v:
                    out[k] = "(omitted)"
                continue
            out[k] = slim(v)
        return out
    if isinstance(value, list):
        return [slim(v) for v in value]
    return value


def _get(obj: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def deadline_for(p: dict[str, Any], started: float, default: int = DEFAULT_WAIT) -> float:
    return started + (P.number(p, "max_wait_seconds", default, 10, MAX_WAIT) or default)


def size_text(n: Any) -> str:
    if not isinstance(n, (int, float)) or n <= 0:
        return ""
    return f"{n / (1024 * 1024):.1f} MB" if n >= 1024 * 1024 else f"{max(1, int(n // 1024))} KB"


# --------------------------------------------------------------------------- accounts and references


def account_of(ref: str | None) -> str | None:
    """The Muse account an asset id, job id or chat id belongs to.

    Asset ids carry the email as hex (user:12345-email:<hex>-image:<sha>.jpg, documented on POST /assets);
    job and chat ids carry it in plain text (...-email:john@gmail.com-task:... / -chat:...).
    """
    if not ref:
        return None
    ref = str(ref)
    match = re.search(r"-email:([0-9a-fA-F]+)-(?:image|video|audio|document|web|podcast|file)\b", ref)
    if match and len(match.group(1)) % 2 == 0:
        try:
            email = bytes.fromhex(match.group(1)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            email = ""
        if "@" in email:
            return email
    match = re.search(r"-email:([^\s]+?@[^\s]+?)-(?:chat|task|bot):", ref)
    return match.group(1) if match else None


def kind_of(ref: str) -> str | None:
    """image, video or audio for a Muse asset id, else None (a workspace path or another kind)."""
    match = re.search(r"-email:[0-9a-fA-F]+-(image|video|audio):", str(ref))
    return match.group(1) if match else None


def need_email(ctx: Ctx, p: dict[str, Any]) -> str:
    """Tools that read one account's data need an email. With one connected account, use it."""
    email = ctx.email(p)
    if email:
        return email
    accounts = ctx.get("accounts")
    emails = list(accounts) if isinstance(accounts, dict) else []
    if len(emails) == 1:
        return emails[0]
    if not emails:
        raise UseapiError(f"No Muse account is connected to useapi.net yet. Connect one first: {SETUP_ACCOUNT_URL}")
    raise UseapiError(
        "Parameter 'email' is required here: say which Muse account to read. "
        f"Connected: {', '.join(emails)}. You can also set a default email in the plugin's credentials."
    )


def _file_payload(file: Any, want: str | None = None) -> tuple[bytes, str, str]:
    """(bytes, MIME type, kind) of a Dify file, checked against what POST /assets accepts."""
    blob = getattr(file, "blob", None)
    if blob is None:
        raise UseapiError("Could not read the uploaded file.")
    name = getattr(file, "filename", None)
    mime = (getattr(file, "mime_type", None) or "").lower().strip()
    mime = MIME_ALIASES.get(mime, mime)
    if mime not in UPLOAD_TYPES:
        ext = (getattr(file, "extension", None) or (name or "").rsplit(".", 1)[-1] or "").lower().lstrip(".")
        mime = EXT_TYPES.get(ext, mime)
    if mime not in UPLOAD_TYPES:
        raise UseapiError(
            "Muse accepts JPEG, PNG and WebP images, MP4, MOV and WebM videos, and MP3, WAV, M4A and OGG audio, up to 50 MB each."
        )
    kind = UPLOAD_TYPES[mime]
    if want and kind != want:
        raise UseapiError(f"This parameter takes {want} files, and this file is {kind} ({mime}).")
    if len(blob) > MAX_UPLOAD_BYTES:
        raise UseapiError(f"The file is {len(blob) // (1024 * 1024)} MB. Muse accepts files up to 50 MB.")
    if not blob:
        raise UseapiError("The file is empty.")
    return blob, mime, kind


class Refs:
    """Collects the input files of one request and uploads Dify files to the right Muse account.

    All inputs of one job or chat must live on the same Muse account (catalog `pins_account`), so uploads go to the
    account of the asset ids given, else to the tool's or the credentials' email, else to the account of the first upload.
    """

    def __init__(self, ctx: Ctx, p: dict[str, Any], email: str | None = None):
        self.ctx = ctx
        self.email: str | None = email or P.text(p, "email")
        self.uploaded: list[str] = []

    def pin(self, ref: str | None) -> None:
        if ref and not self.email:
            self.email = account_of(ref)

    def finish_pinning(self) -> None:
        """No id pinned an account: fall back to the credentials' default email (or let useapi.net pick)."""
        if not self.email:
            self.email = self.ctx.default_email

    def upload(self, file: Any, want: str | None = None) -> str:
        blob, mime, _kind = _file_payload(file, want)
        data = self.ctx.client.request("POST", "assets", params={"email": self.email}, data=blob, content_type=mime, timeout=UPLOAD_TIMEOUT)
        ref = data.get("assetId") if isinstance(data, dict) else None
        if not ref:
            raise UseapiError("Muse did not return an asset id for the uploaded file. Try again.")
        if not self.email:
            self.email = data.get("email") or account_of(ref)
        self.uploaded.append(ref)
        return ref


def gather(refs: Refs, p: dict[str, Any], slots: list[tuple[str, str, str, int]]) -> dict[str, Any]:
    """Resolve input slots into API fields image_1.., video_1.., audio_1...

    slots: (kind, id parameter, file parameter, max items). Ids are pinned first, so uploads land on
    the account the ids belong to. Ids come first, then the files, in the order given.
    """
    ids: dict[str, list[str]] = {}
    for kind, id_param, _file_param, limit in slots:
        values = P.items(p, id_param)
        if len(values) > limit:
            raise UseapiError(f"Parameter '{id_param}' takes at most {limit} item(s).")
        for value in values:
            found = kind_of(value)
            if found and found != kind:
                raise UseapiError(f"'{id_param}' takes {kind} asset ids, and {value} is a {found}.")
            refs.pin(value)
        ids[kind] = values
    refs.finish_pinning()
    fields: dict[str, Any] = {}
    for kind, id_param, file_param, limit in slots:
        values = list(ids[kind])
        for file in P.files(p, file_param):
            values.append(refs.upload(file, kind))
        if len(values) > limit:
            raise UseapiError(f"'{id_param}' and '{file_param}' take at most {limit} {kind}(s) together.")
        for n, value in enumerate(values, 1):
            fields[f"{kind}_{n}"] = value
    return fields


def compose_prompt(p: dict[str, Any]) -> str:
    """The prompt, with the aspect ratio asked for the way Muse follows best ("in exactly <ratio> aspect ratio")."""
    prompt = P.required(p, "prompt")
    ratio = P.text(p, "aspect_ratio")
    if ratio and ratio != "auto" and "aspect ratio" not in prompt.lower():
        prompt = f"In exactly {ratio} aspect ratio: {prompt}"
    if len(prompt) > MAX_PROMPT:
        raise UseapiError(f"The prompt is {len(prompt)} characters. Muse takes up to {MAX_PROMPT}.")
    return prompt


# --------------------------------------------------------------------------- file outputs


SAFE_ATTACH_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/x-m4a",
        "audio/ogg",
        "application/pdf",
        "text/plain",
        "text/markdown",
    }
)
HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
PDF_HINT = "A PDF version is available: use 'Download a Muse file' with the asset id and Format = PDF."


def safe_attachment(mime: str) -> tuple[str, str | None, str | None]:
    """(MIME type to attach, extra file suffix, note) so that no file served by Dify can run active content."""
    base = (mime or "").split(";")[0].strip().lower()
    if base in SAFE_ATTACH_TYPES:
        return base, None, None
    if base in HTML_TYPES:
        return (
            "text/plain",
            ".html.txt",
            f"An HTML document is attached as plain text (.html.txt) so it cannot run in the browser. {PDF_HINT}",
        )
    return (
        "application/octet-stream",
        ".bin",
        f"A file of type {base or 'unknown'} is attached as an opaque .bin file; its type is not one Dify can show safely.",
    )


def file_name(stem: str, n: int, count: int, mime: str, server_name: str | None) -> str:
    """Name of the attached file, consistent with the type actually attached (see safe_attachment)."""
    _, suffix, _ = safe_attachment(mime)
    base = f"{stem}-{n}" if count > 1 else stem
    if suffix:
        return base + suffix
    ext = FILE_EXT.get((mime or "").split(";")[0].strip().lower())
    if not ext and server_name and "." in server_name:
        ext = re.sub(r"[^A-Za-z0-9]", "", server_name.rsplit(".", 1)[-1])[:8]
    return f"{base}.{ext or 'bin'}"


def files_out(ctx: Ctx, assets: list[dict[str, Any]], stem: str) -> Iterator[Out]:
    """Attach finished files as Dify files, downloaded with GET /assets/{assetId}."""
    assets = [a for a in assets if isinstance(a, dict) and a.get("assetId")]
    for n, asset in enumerate(assets, 1):
        budget = ctx.download_budget()
        if budget <= 0:
            yield text(
                "The remaining files were not attached because of time (Dify stops a tool call at 600 seconds). "
                "Download them with 'Download a Muse file' and their asset ids."
            )
            return
        size = asset.get("bytes")
        if isinstance(size, (int, float)) and size > MAX_FILE_BYTES:
            yield text(f"File {n} is {size_text(size)}, too large to attach. Download it with 'Download a Muse file'.")
            continue
        try:
            blob, mime, server_name = ctx.client.download_asset(asset["assetId"], max_bytes=MAX_FILE_BYTES, budget=budget)
        except FileTooLarge as e:
            yield text(f"File {n} is {size_text(e.size)}, too large to attach. Download it with 'Download a Muse file'.")
            continue
        except UseapiError as e:
            yield text(f"File {n} could not be attached: {e} Its asset id is {asset['assetId']}.")
            continue
        mime = mime if mime and mime != "application/octet-stream" else (asset.get("mime") or "application/octet-stream")
        safe_mime, _, note = safe_attachment(mime)
        if note:
            yield text(f"File {n}: {note}")
        yield Out("blob", blob, meta={"mime_type": safe_mime, "filename": file_name(stem, n, len(assets), mime, server_name)})


def asset_lines(assets: list[dict[str, Any]]) -> list[str]:
    lines = []
    for n, a in enumerate(assets, 1):
        extra = ", ".join(x for x in (a.get("mime"), size_text(a.get("bytes"))) if x)
        lines.append(f"{n}. {a.get('type') or 'file'}{f' ({extra})' if extra else ''}: {a.get('assetId')}")
    return lines


# --------------------------------------------------------------------------- jobs


def job_failure_text(job: dict[str, Any]) -> str:
    """A failed job's error.code, explained as the job error table of GET /jobs/{jobid} does."""
    error = job.get("error") if isinstance(job.get("error"), dict) else {}
    code = error.get("code")
    said = str(error.get("message") or "").strip()
    low = said.lower()
    run_again = "run it again now" in low  # the API's words when the job was not tied to the account: a new run goes elsewhere
    retry_at = error.get("retryAt")
    kind = job.get("type") or "generation"
    if code == 403 and "switched off video" in low:
        line = (
            "Nothing was made (403): Meta has switched off video for this Muse account in its country or region. Image jobs still work on it. "
            + ("Run it again now: video jobs go to your other accounts." if run_again else "Run videos on another Muse account.")
        )
    elif code == 403 and "asked for permission" in low:
        line = (
            "Nothing was made (403): Muse asked for permission before it could go on, and a job cannot answer that. "
            "Run the request as a Muse chat (chat), then answer the request with answer_approval."
        )
    elif code == 403:
        line = f"Muse refused to make this {kind} (403). Sending the same prompt again will not help: change the prompt or the inputs."
    elif code == 409:
        line = (
            "Nothing was made (409): Muse says this account already made this request or already has it queued, and would not do it again. "
            "Muse keeps what it made across chats, so the same prompt on the same account gets the same answer. "
            "Change the prompt, or run it on another Muse account (leave the email empty)."
        )
    elif code == 412:
        line = (
            "The account's weekly Muse allowance is used up (412). It counts again after the reset time: 'Get Muse account usage' shows it."
        )
    elif code == 429 and (retry_at or "video limit" in low):
        line = "Nothing was made (429): the account reached Muse's video limit for the last 24 hours. Image jobs still work. " + (
            f"Video jobs try this account again after {retry_at}."
            if retry_at
            else "Run it again now: video jobs go to your other accounts."
        )
    elif code == 429 and "usage limit" in low:
        line = "Nothing was made (429): Muse says a usage limit on the account stopped the job. Retry later, or run it on another Muse account."
    elif code == 429:
        line = "Nothing was made (429): Muse is limiting requests on the account right now. Run it again in about a minute."
    elif code == 502:
        line = (
            "Muse made a file the API cannot return, or did not accept the message (502). Running the job again uses the allowance again. "
            "Report the jobid to support@useapi.net."
        )
    elif code == 503:
        line = "Nothing was made (503): Muse could not be reached, or failed to make it this time. Run it again: the same prompt usually works on the next try."
    elif code == 504:
        line = (
            "Muse did not finish in time, or the connection dropped (504). The file may still be in the account's Muse chat, "
            "so check 'List Muse chats' before running it again."
        )
    elif code == 596:
        line = (
            "The Muse account needs attention and is paused (596). Sign in at https://muse.ai in a browser to see what it needs "
            f"(Meta's security check, or Muse support to restore its computer), then add the account again: {SETUP_ACCOUNT_URL}"
        )
    elif code == 404:
        line = "The account was removed before the job's result could be read (404)."
    else:
        line = f"The {kind} job failed ({code or 'no code'})."
    if said:
        line += f" Details: {said[:800]}"  # the API's message, with Muse's own words inside it
    return line + f" jobid: {job.get('jobid')}"


def _poll(ctx: Ctx, job: dict[str, Any], deadline: float) -> dict[str, Any]:
    while job.get("status") == "started" and job.get("jobid"):
        remaining = deadline - ctx.clock()
        if remaining <= 0:
            break
        ctx.sleep(min(POLL_SECONDS, remaining))
        try:
            fresh = ctx.get(f"jobs/{enc(job['jobid'])}")
        except UseapiError as e:
            if e.status in (403, 404, 410):
                raise
            continue  # a hiccup (5xx, network) must not end the tool: the job keeps running
        if isinstance(fresh, dict) and fresh:
            job = fresh
    return job


def finish_job(ctx: Ctx, answer: Any, p: dict[str, Any], started: float, stem: str, default_wait: int = DEFAULT_WAIT) -> Iterator[Out]:
    job = answer if isinstance(answer, dict) else {}
    if P.flag(p, "wait", True):
        job = _poll(ctx, job, deadline_for(p, started, default_wait))
    status = job.get("status")
    jobid = job.get("jobid")
    if status == "failed":
        raise UseapiError(job_failure_text(job), status=_get(job, "error", "code"), body=job)
    if status != "completed":
        yield text(
            f"Muse is still working on it (job {jobid}, status {status or 'unknown'}). "
            "Call 'Get job status' (get_job) with this jobid and wait=true to get the result and the files. "
            "Do not start the generation again: a repeated prompt can be refused by Muse."
        )
        yield js(slim(job))
        yield var("jobid", jobid)
        yield var("status", status)
        return
    assets = [a for a in _get(job, "result", "assets") or [] if isinstance(a, dict)]
    reply = _get(job, "result", "text")
    kind = job.get("type") or (assets[0].get("type") if assets else "file")
    lines = [f"Muse made the {kind} on {job.get('email') or 'the account useapi.net picked'}. jobid: {jobid}"]
    lines += asset_lines(assets)
    if assets:
        lines.append("Pass an asset id as an input of the next image or video job, or to 'Download a Muse file'.")
    else:
        lines.append("The job finished without a file. Check it with 'Get job status' in a minute.")
    if reply:
        lines.append(f"Muse said: {reply}")
    yield text("\n".join(lines))
    yield js(slim(job))
    yield var("jobid", jobid)
    yield var("status", status)
    yield var("asset_ids", [a["assetId"] for a in assets if a.get("assetId")])
    yield var("reply", reply)
    if P.flag(p, "return_file", True):
        yield from files_out(ctx, assets, stem)


def submit_job(ctx: Ctx, path: str, body: dict[str, Any], p: dict[str, Any]) -> Any:
    """Jobs run in async mode (sync mode holds a request for about 100 seconds) and are polled every 10 seconds."""
    P.put(body, "replyUrl", P.text(p, "reply_url"))
    return ctx.post(path, {**body, "async": True}, timeout=SUBMIT_TIMEOUT)


# --------------------------------------------------------------------------- accounts and jobs tools


def _quota_text(info: dict[str, Any]) -> str:
    quota = info.get("quota") if isinstance(info.get("quota"), dict) else {}
    parts = []
    tier = quota.get("tier")
    if tier:
        parts.append(f"plan {PLAN_NAMES.get(tier, tier)}")
    if quota.get("percentUsed") is not None:
        parts.append(f"{quota['percentUsed']}% of the weekly allowance used")
    if quota.get("resetsAt"):
        parts.append(f"resets {quota['resetsAt']}")
    if quota.get("topupLabel"):
        parts.append(f"top-up {quota['topupLabel']}")
    if info.get("videoLimitUntil"):
        parts.append(f"video limit reached: video jobs skip it until {info['videoLimitUntil']}")
    if info.get("videoRegionBlocked"):
        parts.append("video switched off by Meta in its country or region (image jobs still work)")
    return ", ".join(parts)


@tool("list_accounts")
def list_accounts(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    data = ctx.get("accounts")
    accounts = data if isinstance(data, dict) else {}
    healthy = [e for e, i in accounts.items() if isinstance(i, dict) and i.get("health") == "OK"]
    lines = [f"{len(accounts)} Muse account(s) connected, {len(healthy)} healthy."]
    for email, info in accounts.items():
        info = info if isinstance(info, dict) else {}
        health = str(info.get("health", "?"))
        state = "OK" if health == "OK" else "needs attention: " + health[:300]
        quota = _quota_text(info)
        lines.append(
            f"- {email}: {state}" + (f"; {quota}" if quota else "") + (f"; maxJobs {info['maxJobs']}" if info.get("maxJobs") else "")
        )
    if not accounts:
        lines.append(f"Connect a Muse account first: {SETUP_ACCOUNT_URL}")
    elif len(healthy) > 1:
        lines.append("With the email left empty, a new job goes to a healthy account with allowance left and a free job slot.")
    lines.append("Usage here is as last read; 'Get Muse account usage' reads it live.")
    yield var("emails", list(accounts.keys()))
    yield var("healthy_emails", healthy)
    yield from done("\n".join(lines), slim(data))


@tool("get_account")
def get_account(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    email = need_email(ctx, p)
    data = ctx.get(f"accounts/{enc(email)}", timeout=ACCOUNT_TIMEOUT)
    data = data if isinstance(data, dict) else {}
    quota = data.get("quota") if isinstance(data.get("quota"), dict) else {}
    lines = [
        f"Muse account {email}: health {data.get('health', '?')}" + (f", session {data['session']}" if data.get("session") else "") + "."
    ]
    summary = _quota_text(data)
    if summary:
        lines.append(summary[0].upper() + summary[1:] + ".")
    if quota.get("quotaStatus") and quota.get("quotaStatus") != "SUFFICIENT":
        lines.append(f"Quota status {quota['quotaStatus']}: new jobs go to other accounts until the reset.")
    if data.get("quotaError"):
        lines.append(f"Muse did not answer the live read: {data['quotaError']}")
    tier = quota.get("tier")
    yield var("plan", PLAN_NAMES.get(tier, tier) if tier else None)
    yield var("percent_used", quota.get("percentUsed"))
    yield var("resets_at", quota.get("resetsAt"))
    yield from done("\n".join(lines), slim(data))


@tool("list_jobs")
def list_jobs(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    data = ctx.get("jobs")
    data = data if isinstance(data, dict) else {}
    running = [j for j in data.get("running") or [] if isinstance(j, dict)]
    lines = [f"{len(running)} Muse job(s) running now."]
    for j in running[:50]:
        lines.append(f"- {j.get('type')} on {j.get('email')}, since {j.get('created')}: {j.get('jobid')}")
    for email, slots in (data.get("accounts") or {}).items():
        if isinstance(slots, dict):
            lines.append(f"- {email}: {slots.get('running', 0)} of {slots.get('maxJobs', '?')} job slots in use")
    yield var("jobids", [j.get("jobid") for j in running if j.get("jobid")])
    yield from done("\n".join(lines), slim(data))


@tool("get_job")
def get_job(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    jobid = P.required(p, "jobid")
    job = ctx.get(f"jobs/{enc(jobid)}")
    stem = "muse-video" if (isinstance(job, dict) and job.get("type") == "video") else "muse-image"
    yield from finish_job(ctx, job, p, started, stem)


# --------------------------------------------------------------------------- generation tools

IMAGE_SLOT = ("image", "images", "image_files", 9)


@tool("generate_image")
def generate_image(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    body: dict[str, Any] = {"prompt": compose_prompt(p)}
    refs = Refs(ctx, p)
    body.update(gather(refs, p, [IMAGE_SLOT]))
    P.put(body, "email", refs.email)
    answer = submit_job(ctx, "jobs/image", body, p)
    yield from finish_job(ctx, answer, p, started, "muse-image")


@tool("generate_video")
def generate_video(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    body: dict[str, Any] = {"prompt": compose_prompt(p)}
    refs = Refs(ctx, p)
    body.update(gather(refs, p, [IMAGE_SLOT, ("video", "videos", "video_files", 3), ("audio", "audio", "audio_files", 3)]))
    P.put(body, "email", refs.email)
    answer = submit_job(ctx, "jobs/video", body, p)
    yield from finish_job(ctx, answer, p, started, "muse-video", VIDEO_WAIT)


# --------------------------------------------------------------------------- Library tools


@tool("upload_file")
def upload_file(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    file = p.get("file")
    url = P.text(p, "url")
    email = ctx.email(p)
    if file is not None and file != "":
        refs = Refs(ctx, p)
        refs.finish_pinning()
        ref = refs.upload(file)
        data: dict[str, Any] = {"assetId": ref, "email": refs.email}
        email = refs.email
    elif url:
        if not url.lower().startswith("https://"):
            raise UseapiError("Parameter 'url' must be a public https URL of the file.")
        data = ctx.client.request("POST", "assets", params={"email": email}, body={"url": url}, timeout=UPLOAD_TIMEOUT)
        data = data if isinstance(data, dict) else {}
        ref = data.get("assetId")
        if not ref:
            raise UseapiError("Muse did not return an asset id for the file. Try again.")
        email = data.get("email") or email or account_of(ref)
    else:
        raise UseapiError("Give a file in 'file', or a public https URL of the file in 'url'.")
    kind = kind_of(ref) or data.get("type") or "file"
    yield var("asset_id", ref)
    yield var("email", email)
    yield text(
        f"Uploaded the {kind} to Muse account {email or '(picked by useapi.net)'}. asset id: {ref}\n"
        f"Pass it as an input ({kind}s) of Generate image, Generate video or Muse chat. It works only with inputs of the same Muse account."
    )
    yield js(data)


@tool("list_assets")
def list_assets(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    email = need_email(ctx, p)
    query = {
        "email": email,
        "type": P.text(p, "type"),
        "origin": P.text(p, "origin"),
        "limit": P.number(p, "limit", None, 1, 100),
        "cursor": P.text(p, "cursor"),
    }
    data = ctx.get("assets", params=query)
    data = data if isinstance(data, dict) else {}
    assets = [a for a in data.get("assets") or [] if isinstance(a, dict)]
    lines = [f"{len(assets)} item(s) in the Muse Library of {email}, newest first."]
    for a in assets:
        origin = f", {a['origin']}" if a.get("origin") else ""
        name = f' "{a["name"]}"' if a.get("name") else ""
        lines.append(
            f"- {a.get('type')}{origin}{name}, {a.get('updated') or a.get('created') or ''}: {a.get('assetId') or '(not downloadable)'}"
        )
    if data.get("partial"):
        lines.append("The list may be incomplete: a part of the Library could not be read right now.")
    if data.get("cursor"):
        lines.append(f"More items: call again with cursor = {data['cursor']}")
    yield var("asset_ids", [a.get("assetId") for a in assets if a.get("assetId")])
    yield var("cursor", data.get("cursor"))
    yield from done("\n".join(lines), slim(data))


@tool("get_asset")
def get_asset(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    ref = P.required(p, "asset_id")
    fmt = P.text(p, "format")
    params = {"format": fmt} if fmt else None
    try:
        blob, mime, server_name = ctx.client.download_asset(ref, params=params, max_bytes=MAX_FILE_BYTES, budget=ctx.download_budget())
    except FileTooLarge as e:
        raise UseapiError(f"The file is {size_text(e.size)}, larger than the 150 MB this plugin attaches.") from e
    kind = kind_of(ref) or "file"
    name = file_name(f"muse-{kind}", 1, 1, mime, server_name)
    safe_mime, _, note = safe_attachment(mime)
    yield text(
        f"Downloaded the {kind} ({mime}, {size_text(len(blob)) or '0 KB'}). The file is attached as {name}." + (f" {note}" if note else "")
    )
    yield js({"assetId": ref, "mime": mime, "bytes": len(blob), "filename": server_name})
    yield var("mime_type", mime)
    yield Out("blob", blob, meta={"mime_type": safe_mime, "filename": name})


# --------------------------------------------------------------------------- Muse chat


def _chat_path(chat_id: str) -> str:
    return f"chats/{enc(chat_id)}"


def _messages(chat: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in chat.get("messages") or [] if isinstance(m, dict)]


def _reply(chat: dict[str, Any], after_id: str | None, my_text: str | None = None) -> tuple[list[dict[str, Any]], bool]:
    """The agent messages after a marker message. (messages, marker found)

    The marker is the message with after_id; without one, the latest user message with the text just sent (my_text);
    without that either, the latest user message.
    """
    messages = _messages(chat)
    index = None
    for i, m in enumerate(messages):
        if after_id:
            hit = m.get("messageId") == after_id
        elif my_text is not None:
            hit = m.get("role") == "user" and str(m.get("text") or "").strip() == my_text.strip()
        else:
            hit = m.get("role") == "user"
        if hit:
            index = i
    if index is None:
        marked = bool(after_id) or my_text is not None
        return ([] if marked else [m for m in messages if m.get("role") == "assistant"]), False
    return [m for m in messages[index + 1 :] if m.get("role") == "assistant"], True


def _pending(chat: dict[str, Any], skip: str | None = None) -> list[dict[str, Any]]:
    return [a for a in chat.get("pendingApprovals") or [] if isinstance(a, dict) and a.get("approvalId") != skip]


def _read_chat(ctx: Ctx, chat_id: str) -> dict[str, Any]:
    chat = ctx.get(_chat_path(chat_id), params={"limit": CHAT_PAGE})
    return chat if isinstance(chat, dict) else {}


def _follow(
    ctx: Ctx,
    chat_id: str,
    deadline: float,
    after_id: str | None,
    need_reply: bool,
    answered: str | None = None,
    my_text: str | None = None,
) -> dict[str, Any]:
    """Read the chat every 10 seconds until Muse's answer ends, a permission request waits, or the wait runs out."""
    chat: dict[str, Any] = {}
    while True:
        try:
            chat = _read_chat(ctx, chat_id)
        except UseapiError as e:
            if not chat or e.status in (400, 401, 403, 404):
                raise
            # a hiccup (5xx, network) must not end the tool: Muse keeps answering. Keep the last read.
        replies, found = _reply(chat, after_id, my_text)
        pending = _pending(chat, answered)
        answered_open = bool(answered) and any(a.get("approvalId") == answered for a in chat.get("pendingApprovals") or [])
        idle = chat.get("status") not in CHAT_BUSY
        settled = bool(pending) or (idle and not answered_open and (found or not (after_id or my_text)) and (replies or not need_reply))
        remaining = deadline - ctx.clock()
        if settled or remaining <= 0:
            return chat
        ctx.sleep(min(POLL_SECONDS, remaining))


def chat_out(
    ctx: Ctx, chat: dict[str, Any], chat_id: str, p: dict[str, Any], after_id: str | None, my_text: str | None = None
) -> Iterator[Out]:
    replies, _found = _reply(chat, after_id, my_text)
    pending = _pending(chat)
    if pending:
        status = "waiting_for_approval"
    elif not replies:
        status = "running"  # nothing after the message yet: Muse has not answered it (or not within the wait)
    else:
        status = chat.get("status") or "unknown"
    texts = [str(m.get("text")).strip() for m in replies if str(m.get("text") or "").strip()]
    files = [f for m in replies for f in m.get("files") or [] if isinstance(f, dict) and f.get("assetId")]
    widgets = [w for m in replies for w in m.get("widgets") or [] if isinstance(w, dict)]
    lines = ["\n\n".join(texts) or "(Muse has not replied yet)"]
    if files:
        lines.append("Files Muse made:")
        lines += asset_lines(files)
    for w in widgets:
        if w.get("options"):
            lines.append(
                "Muse offers quick replies: " + " / ".join(str(o) for o in w["options"]) + ". Send the one you want as the next message."
            )
        elif w.get("fallbackText") or w.get("text"):
            lines.append(f"Muse shows a {w.get('kind') or 'card'}: {w.get('fallbackText') or w.get('text')}")
    for a in pending:
        offered = [str(o.get("decision")) for o in a.get("options") or [] if isinstance(o, dict) and o.get("decision") != "allow_always"]
        choices = ", ".join(offered) or "allow_once, deny"
        lines.append(
            f"Muse asks for permission: {a.get('question') or a.get('title') or ''} (approval_id {a.get('approvalId')}, choices {choices}"
            + (f", expires {a['expires']}" if a.get("expires") else "")
            + "). Ask the user, then call 'Answer a Muse permission request' (answer_approval) with this chat_id and approval_id."
        )
    if status in CHAT_BUSY:
        lines.append(
            "Muse is still working on this answer. Call 'Get Muse chat' (get_chat) with this chat_id and wait=true to read the rest. "
            "Do not send the message again."
        )
    lines.append(f"chat_id: {chat_id} (status {status}, account {chat.get('email') or account_of(chat_id) or '?'})")
    yield text("\n".join(lines))
    summary = {k: chat.get(k) for k in ("chatId", "title", "email", "created", "updated") if chat.get(k) is not None}
    summary.update(
        status=status, chatStatus=chat.get("status"), messages=replies, pendingApprovals=pending, browsers=chat.get("browsers") or []
    )
    yield js(slim(summary))  # this answer only, not the whole chat
    yield var("chat_id", chat_id)
    yield var("status", status)
    yield var("reply", "\n\n".join(texts))
    yield var("asset_ids", [f["assetId"] for f in files])
    yield var("approval_ids", [a.get("approvalId") for a in pending if a.get("approvalId")])
    if P.flag(p, "return_file", True):
        yield from files_out(ctx, files, "muse-chat")


@tool("chat")
def chat(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    chat_id = P.text(p, "chat_id")
    message = P.required(p, "message")
    if len(message) > MAX_PROMPT:
        raise UseapiError(f"The message is {len(message)} characters. Muse takes up to {MAX_PROMPT}.")
    refs = Refs(ctx, p, email=account_of(chat_id) if chat_id else None)  # files must be on the chat's account
    files = P.items(p, "files", split_spaces=False)
    for ref in files:
        refs.pin(ref)
    refs.finish_pinning()
    files += [refs.upload(f) for f in P.files(p, "upload_files")]
    body: dict[str, Any] = {"message": message}
    P.put(body, "files", files)
    if chat_id:
        answer = ctx.post(f"{_chat_path(chat_id)}/messages", body, timeout=CHAT_TIMEOUT)
    else:
        P.put(body, "email", refs.email)
        answer = ctx.post("chats", body, timeout=CHAT_TIMEOUT)
    answer = answer if isinstance(answer, dict) else {}
    chat_id = answer.get("chatId") or chat_id
    if not chat_id:
        raise UseapiError("Muse did not return a chat id. Check 'List Muse chats' before sending the message again.")
    message_id = answer.get("messageId")
    if not P.flag(p, "wait", True):
        yield text(f"Message sent. Muse is answering (chat_id: {chat_id}). Read the answer with 'Get Muse chat' (get_chat) and wait=true.")
        yield js(answer)
        yield var("chat_id", chat_id)
        yield var("status", "running")
        return
    my_text = None if message_id else message  # no messageId: find the message by its text
    state = _follow(ctx, chat_id, deadline_for(p, started), message_id, need_reply=True, my_text=my_text)
    yield from chat_out(ctx, state, chat_id, p, message_id, my_text)


@tool("get_chat")
def get_chat(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    chat_id = P.required(p, "chat_id")
    if P.flag(p, "wait", False):
        state = _follow(ctx, chat_id, deadline_for(p, started), None, need_reply=False)
    else:
        state = _read_chat(ctx, chat_id)
    yield from chat_out(ctx, state, chat_id, p, None)


@tool("answer_approval")
def answer_approval(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    started = ctx.clock()
    chat_id = P.required(p, "chat_id")
    decision = P.required(p, "decision")
    if decision == "allow_always":
        raise UseapiError(
            "This plugin answers a permission request once only (allow_once) or denies it (deny). "
            "To allow a site for good, the user answers 'always' in muse.ai."
        )
    if decision not in ("allow_once", "deny"):
        raise UseapiError("Parameter 'decision' must be allow_once or deny.")
    before = _read_chat(ctx, chat_id)
    pending = _pending(before)
    approval_id = P.text(p, "approval_id")
    if not approval_id:
        if len(pending) != 1:
            ids = ", ".join(str(a.get("approvalId")) for a in pending) or "none"
            raise UseapiError(f"Parameter 'approval_id' is required: {len(pending)} permission request(s) wait in this chat ({ids}).")
        approval_id = str(pending[0].get("approvalId"))
    messages = _messages(before)
    last_id = messages[-1].get("messageId") if messages else None
    ctx.post(f"{_chat_path(chat_id)}/approvals/{enc(approval_id)}", {"decision": decision}, timeout=CHAT_TIMEOUT)
    if not P.flag(p, "wait", True):
        yield text(f"Answered {decision}. Muse goes on (chat_id: {chat_id}). Read the rest with 'Get Muse chat' and wait=true.")
        yield js({"chatId": chat_id, "approvalId": approval_id, "decision": decision})
        yield var("chat_id", chat_id)
        yield var("status", "running")
        return
    state = _follow(ctx, chat_id, deadline_for(p, started), last_id, need_reply=True, answered=approval_id)
    yield from chat_out(ctx, state, chat_id, p, last_id)


@tool("list_chats")
def list_chats(ctx: Ctx, p: dict[str, Any]) -> Iterator[Out]:
    email = need_email(ctx, p)
    data = ctx.get("chats", params={"email": email, "limit": P.number(p, "limit", None, 1, 100), "cursor": P.text(p, "cursor")})
    data = data if isinstance(data, dict) else {}
    chats = [c for c in data.get("chats") or [] if isinstance(c, dict)]
    lines = [f"{len(chats)} Muse chat(s) on {email}, newest first (jobs are chats too)."]
    for c in chats:
        lines.append(f"- {c.get('title') or '(untitled)'} [{c.get('status') or '?'}], updated {c.get('updated') or '?'}: {c.get('chatId')}")
    if data.get("cursor"):
        lines.append(f"More chats: call again with cursor = {data['cursor']}")
    yield var("chat_ids", [c.get("chatId") for c in chats if c.get("chatId")])
    yield var("cursor", data.get("cursor"))
    yield from done("\n".join(lines), slim(data))
