"""Every tool against a mocked HTTP layer: method, path, query and body."""

from __future__ import annotations

import re

import pytest

from fakes import FakeResponse, make_ctx, outs, run, vars_of
from useapi_muse import runner
from useapi_muse.client import UseapiError
from useapi_muse.handlers import HANDLERS, account_of, compose_prompt, kind_of

EMAIL = "john@gmail.com"
OTHER = "jane@gmail.com"
HEX = EMAIL.encode().hex()
IMG = f"user:12345-email:{HEX}-image:3e788737ea18422b9809aeb06a453c072e15f1b3fb219d7a4fd7e8fffd733d4f.jpg"
IMG2 = f"user:12345-email:{HEX}-image:media-generation-a-young-woman-0-df6bcf46.webp"
VID = f"user:12345-email:{HEX}-video:media-generation-shoreline-0-acd2974b.mp4"
AUD = f"user:12345-email:{HEX}-audio:9f2c.mp3"
OTHER_IMG = f"user:12345-email:{OTHER.encode().hex()}-image:aa.jpg"
JOB = "j1012012156286615380v-u12345-email:john@gmail.com-task:20842037-a004-4dba-b640-225a8197385b-bot:muse"
CHAT = "c-u12345-email:john@gmail.com-chat:272b73f4-6fcb-42c2-9ec7-75cc0c020940-bot:muse"
NOWAIT = {"wait": False, "return_file": False}


def job(status="completed", kind="video", assets=None, error=None, **extra):
    record = {"jobid": JOB, "type": kind, "email": EMAIL, "status": status, "request": {"prompt": "x"}, "chatId": "20842037"}
    if status == "completed":
        record["result"] = {
            "assets": assets
            if assets is not None
            else [{"assetId": VID, "type": "video", "mime": "video/mp4", "bytes": 5066535, "origin": "generated"}],
            "text": "Done, here's your clip.",
        }
    if error:
        record["error"] = error
    record.update(extra)
    return record


def chat_record(status="completed", reply="Here it is.", files=None, approvals=None, my_id="m-1", widgets=None):
    messages = [
        {"messageId": "m-0", "role": "user", "text": "earlier", "files": []},
        {"messageId": "a-0", "role": "assistant", "text": "earlier answer", "files": []},
        {"messageId": my_id, "role": "user", "text": "make an image", "files": []},
    ]
    if reply is not None:
        messages.append({"messageId": "a-1", "role": "assistant", "text": reply, "files": [], **({"widgets": widgets} if widgets else {})})
    if files:
        messages.append({"messageId": "a-2", "role": "assistant", "text": "", "files": files})
    return {
        "chatId": CHAT,
        "title": "t",
        "status": status,
        "email": EMAIL,
        "messages": messages,
        "browsers": [],
        "pendingApprovals": approvals or [],
        "hasMore": False,
    }


APPROVAL = {
    "approvalId": "87c8850c",
    "title": "Share info with example.com",
    "question": "Allow Muse to share information with example.com?",
    "details": [],
    "options": [{"decision": "allow_once", "label": "Allow once"}, {"decision": "allow_always"}, {"decision": "deny"}],
    "expires": "2026-10-13T00:42:04.519Z",
}
IMG_FILE = {"assetId": IMG2, "type": "image", "mime": "image/webp", "bytes": 186402, "origin": "generated"}
ACCOUNTS = {EMAIL: {"email": EMAIL, "health": "OK", "maxJobs": 3, "quota": {"tier": "HATCH_FREE", "percentUsed": 3}}}


class FakeFile:
    def __init__(self, blob=b"img", mime="image/png", filename="a.png", extension=".png"):
        self.blob = blob
        self.mime_type = mime
        self.filename = filename
        self.extension = extension


def upload_ok(ref=IMG, email=EMAIL):
    return {"assetId": ref, "email": email, "type": "image", "mime": "image/png", "bytes": 3}


# name, params, method, path, expected query subset, expected body subset
CASES = [
    ("list_accounts", {}, "GET", "accounts", {}, None),
    ("get_account", {"email": EMAIL}, "GET", f"accounts/{EMAIL}", {}, None),
    ("list_jobs", {}, "GET", "jobs", {}, None),
    ("get_job", {"jobid": JOB, **NOWAIT}, "GET", f"jobs/{JOB}", {}, None),
    (
        "generate_image",
        {"prompt": "A red fox in snow", "aspect_ratio": "16:9", "images": f"{IMG}\n{IMG2}", **NOWAIT},
        "POST",
        "jobs/image",
        {},
        {"prompt": "In exactly 16:9 aspect ratio: A red fox in snow", "image_1": IMG, "image_2": IMG2, "email": EMAIL, "async": True},
    ),
    (
        "generate_video",
        {"prompt": "Edit video_1 with image_1", "images": IMG, "videos": VID, "audio": AUD, **NOWAIT},
        "POST",
        "jobs/video",
        {},
        {"prompt": "Edit video_1 with image_1", "image_1": IMG, "video_1": VID, "audio_1": AUD, "email": EMAIL, "async": True},
    ),
    (
        "upload_file",
        {"url": "https://example.com/a.jpg", "email": EMAIL},
        "POST",
        "assets",
        {"email": EMAIL},
        {"url": "https://example.com/a.jpg"},
    ),
    (
        "list_assets",
        {"email": EMAIL, "type": "video", "origin": "generated", "limit": 20, "cursor": "c1"},
        "GET",
        "assets",
        {"email": EMAIL, "type": "video", "origin": "generated", "limit": "20", "cursor": "c1"},
        None,
    ),
    ("get_asset", {"asset_id": VID}, "GET", f"assets/{VID}", {}, None),
    ("chat", {"message": "Hi", "email": EMAIL, "wait": False}, "POST", "chats", {}, {"message": "Hi", "email": EMAIL}),
    ("chat", {"message": "More", "chat_id": CHAT, "wait": False}, "POST", f"chats/{CHAT}/messages", {}, {"message": "More"}),
    ("get_chat", {"chat_id": CHAT, "return_file": False}, "GET", f"chats/{CHAT}", {"limit": "200"}, None),
    ("list_chats", {"email": EMAIL, "limit": 5}, "GET", "chats", {"email": EMAIL, "limit": "5"}, None),
]


@pytest.mark.parametrize("name,params,method,path,query,body", CASES, ids=[f"{c[0]}-{c[3]}" for c in CASES])
def test_request_shape(name, params, method, path, query, body):
    routes = [
        ("GET", "accounts", ACCOUNTS),
        ("POST", "chats", {"chatId": CHAT, "email": EMAIL, "messageId": "m-1"}),
        ("GET", "assets/", FakeResponse(200, content=b"v", headers={"Content-Type": "video/mp4"})),
        ("POST", "assets", upload_ok()),
        ("POST", "jobs/", job(status="started")),
        ("GET", "jobs/", job(status="started")),
    ]
    ctx, session, _ = make_ctx(routes)
    run(HANDLERS[name], ctx, params)
    call = next(c for c in session.calls if c.method == method and c.path == path)
    for k, v in query.items():
        assert call.query.get(k) == v, (k, call.query)
    if body is not None:
        assert call.body == body, call.body


def test_every_handler_has_a_case():
    assert {c[0] for c in CASES} | {"answer_approval"} == set(HANDLERS)


# --------------------------------------------------------------------------- ids and prompts


def test_account_of_and_kind_of():
    assert account_of(IMG) == EMAIL and account_of(VID) == EMAIL
    assert account_of(CHAT) == EMAIL and account_of(JOB) == EMAIL
    assert account_of("workspace/your_files/report.pdf") is None and account_of(None) is None
    assert kind_of(IMG) == "image" and kind_of(VID) == "video" and kind_of(AUD) == "audio" and kind_of("workspace/x.pdf") is None


def test_compose_prompt():
    assert compose_prompt({"prompt": "A fox", "aspect_ratio": "9:16"}) == "In exactly 9:16 aspect ratio: A fox"
    assert compose_prompt({"prompt": "A fox in 4:3 aspect ratio", "aspect_ratio": "9:16"}) == "A fox in 4:3 aspect ratio"
    assert compose_prompt({"prompt": "A fox"}) == "A fox"
    with pytest.raises(UseapiError, match="up to 5000"):
        compose_prompt({"prompt": "x" * 5001})
    with pytest.raises(UseapiError, match="'prompt' is required"):
        compose_prompt({"prompt": "  "})


# --------------------------------------------------------------------------- generation


def test_generate_video_polls_and_attaches_the_file():
    ctx, session, clock = make_ctx(
        [
            ("POST", "jobs/video", job(status="started")),
            ("GET", "jobs/", [job(status="started"), FakeResponse(503, {"error": "x", "code": 503}), job()]),
            ("GET", "assets/", FakeResponse(200, content=b"mp4", headers={"Content-Type": "video/mp4"})),
        ]
    )
    items = run(HANDLERS["generate_video"], ctx, {"prompt": "A paper boat"})
    texts = [o.value for o in outs(items, "text")]
    assert "Muse made the video" in texts[0] and VID in texts[0] and "Done, here's your clip." in texts[0]
    variables = vars_of(items)
    assert variables["jobid"] == JOB and variables["status"] == "completed" and variables["asset_ids"] == [VID]
    blob = outs(items, "blob")[0]
    assert blob.value == b"mp4" and blob.meta == {"mime_type": "video/mp4", "filename": "muse-video.mp4"}
    assert clock.sleeps == [10, 10, 10]
    submit = next(c for c in session.calls if c.method == "POST")
    assert submit.body == {"prompt": "A paper boat", "async": True}  # no email: useapi.net picks the account


def test_generate_video_default_wait_is_180_seconds():
    ctx, _, clock = make_ctx([("POST", "jobs/video", job(status="started")), ("GET", "jobs/", job(status="started"))])
    items = run(HANDLERS["generate_video"], ctx, {"prompt": "x", "return_file": False})
    assert sum(clock.sleeps) == 180
    assert "get_job" in outs(items, "text")[0].value and vars_of(items)["jobid"] == JOB


def test_generate_image_waits_120_by_default_and_names_webp():
    image = {"assetId": IMG2, "type": "image", "mime": "image/webp", "bytes": 487120, "origin": "generated"}
    ctx, _, clock = make_ctx(
        [
            ("POST", "jobs/image", job(status="started", kind="image")),
            ("GET", "jobs/", job(kind="image", assets=[image])),
            ("GET", "assets/", FakeResponse(200, content=b"webp", headers={"Content-Type": "image/webp"})),
        ]
    )
    items = run(HANDLERS["generate_image"], ctx, {"prompt": "A fox"})
    assert outs(items, "blob")[0].meta == {"mime_type": "image/webp", "filename": "muse-image.webp"}
    assert clock.sleeps == [10]


def test_uploads_go_to_the_account_of_the_ids():
    ctx, session, _ = make_ctx([("POST", "assets", upload_ok(IMG2)), ("POST", "jobs/image", job(status="started"))])
    run(HANDLERS["generate_image"], ctx, {"prompt": "image_1 and image_2", "images": IMG, "image_files": [FakeFile()], **NOWAIT})
    upload = next(c for c in session.calls if c.path == "assets")
    assert upload.query == {"email": EMAIL} and upload.data == b"img" and upload.headers["Content-Type"] == "image/png"
    submit = next(c for c in session.calls if c.path == "jobs/image")
    assert submit.body["image_1"] == IMG and submit.body["image_2"] == IMG2 and submit.body["email"] == EMAIL


def test_first_upload_picks_the_account_for_the_rest():
    ctx, session, _ = make_ctx([("POST", "assets", upload_ok(OTHER_IMG, OTHER)), ("POST", "jobs/image", job(status="started"))])
    run(HANDLERS["generate_image"], ctx, {"prompt": "x", "image_files": [FakeFile(), FakeFile(b"b")], **NOWAIT})
    uploads = [c for c in session.calls if c.path == "assets"]
    assert uploads[0].query == {} and uploads[1].query == {"email": OTHER}
    assert next(c for c in session.calls if c.path == "jobs/image").body["email"] == OTHER


def test_default_email_from_credentials():
    ctx, session, _ = make_ctx([("POST", "jobs/image", job(status="started"))], email=OTHER)
    run(HANDLERS["generate_image"], ctx, {"prompt": "x", **NOWAIT})
    assert session.calls[0].body["email"] == OTHER


@pytest.mark.parametrize(
    "params,error",
    [
        ({"images": VID}, "takes image asset ids"),
        ({"videos": IMG}, "takes video asset ids"),
        ({"images": "\n".join([IMG] * 10)}, "at most 9"),
        ({"videos": "\n".join([VID] * 4)}, "at most 3"),
        ({"image_files": [FakeFile(mime="video/mp4", filename="a.mp4", extension=".mp4")]}, "takes image files"),
        ({"audio_files": [FakeFile(mime="application/pdf", filename="a.pdf", extension=".pdf")]}, "up to 50 MB each"),
        ({"image_files": [FakeFile(blob=b"x" * (50 * 1024 * 1024 + 1))]}, "up to 50 MB"),
    ],
)
def test_input_validation(params, error):
    ctx, session, _ = make_ctx([("POST", "assets", upload_ok())])
    with pytest.raises(UseapiError, match=error):
        run(HANDLERS["generate_video"], ctx, {"prompt": "x", **params, **NOWAIT})
    assert not [c for c in session.calls if c.path.startswith("jobs")]


def test_file_type_from_extension_when_mime_is_missing():
    ctx, session, _ = make_ctx([("POST", "assets", upload_ok(AUD)), ("POST", "jobs/video", job(status="started"))])
    run(HANDLERS["generate_video"], ctx, {"prompt": "x", "audio_files": [FakeFile(b"a", "", "song.m4a", ".m4a")], **NOWAIT})
    assert next(c for c in session.calls if c.path == "assets").headers["Content-Type"] == "audio/x-m4a"


@pytest.mark.parametrize(
    "error,expected",
    [
        ({"code": 409, "message": "Already delivered earlier on Nov 10, so I skipped it."}, "already made this request"),
        ({"code": 403, "message": "I can't help with that."}, "will not help"),
        ({"code": 412, "message": "allowance used up"}, "weekly Muse allowance"),
        (
            {"code": 429, "message": "video limit", "retryAt": "2026-10-23T14:12:41.001Z"},
            "try this account again after 2026-10-23T14:12:41.001Z",
        ),
        ({"code": 429, "message": "limiting"}, "about a minute"),
        # the API's own failure texts (v1-muse settle()): an unpinned job runs again on another account; an approval needs a chat
        (
            {
                "code": 403,
                "message": "Meta has switched off video for account john@gmail.com in its country or region (Muse said: not available). "
                "Run it again now: video jobs go to your other accounts",
            },
            "Run it again now",
        ),
        (
            {"code": 403, "message": "Muse asked for permission (an approval) before it could go on. A job cannot answer approvals"},
            "Run the request as a Muse chat",
        ),
        (
            {
                "code": 429,
                "message": "Account john@gmail.com reached Muse's video limit for the last 24 hours, nothing was made (Muse said: limit). "
                "Run it again now: video jobs go to your other accounts, and this one sits out until 2026-10-23T14:12:00.000Z",
            },
            "Run it again now: video jobs go to your other accounts.",
        ),
        (
            {"code": 429, "message": "Muse says a usage limit on account john@gmail.com stopped it, nothing was made"},
            "Retry later, or run it on another Muse account",
        ),
        ({"code": 502, "message": "odd file name"}, "uses the allowance again"),
        ({"code": 503, "message": "the video worker glitched out"}, "Run it again"),
        ({"code": 504, "message": "timeout"}, "may still be"),
        ({"code": 596, "message": "checkpoint"}, "https://muse.ai"),
    ],
)
def test_failed_jobs_explain_the_code(error, expected):
    record = job(status="failed", error=error)
    ctx, _, _ = make_ctx([("POST", "jobs/video", job(status="started")), ("GET", "jobs/", record)])
    with pytest.raises(UseapiError) as e:
        run(HANDLERS["generate_video"], ctx, {"prompt": "x"})
    assert expected in str(e.value) and error["message"] in str(e.value) and JOB in str(e.value)
    assert e.value.status == error["code"]
    assert not re.search(r"reset (the|this|your|it)\b|/reset", str(e.value), re.IGNORECASE)  # never advise a reset


def test_poll_stops_on_expired_job():
    ctx, _, _ = make_ctx([("GET", "jobs/", [job(status="started"), FakeResponse(410, {"error": "Job has expired", "code": 410})])])
    with pytest.raises(UseapiError, match="7 days"):
        run(HANDLERS["get_job"], ctx, {"jobid": JOB})


def test_large_file_is_not_attached():
    big = [{"assetId": VID, "type": "video", "mime": "video/mp4", "bytes": 200 * 1024 * 1024}]
    ctx, session, _ = make_ctx([("GET", "jobs/", job(assets=big))])
    items = run(HANDLERS["get_job"], ctx, {"jobid": JOB})
    assert any("too large to attach" in o.value for o in outs(items, "text"))
    assert not outs(items, "blob") and not [c for c in session.calls if c.path.startswith("assets")]


def test_failed_download_is_reported_not_raised():
    ctx, _, _ = make_ctx([("GET", "jobs/", job()), ("GET", "assets/", FakeResponse(503, {"error": "Could not connect", "code": 503}))])
    items = run(HANDLERS["get_job"], ctx, {"jobid": JOB})
    assert any("could not be attached" in o.value and VID in o.value for o in outs(items, "text"))


def test_no_download_after_the_deadline():
    ctx, session, clock = make_ctx([("GET", "jobs/", job())])
    clock.t = 600
    items = run(HANDLERS["get_job"], ctx, {"jobid": JOB, "wait": False})
    assert any("because of time" in o.value for o in outs(items, "text"))
    assert not [c for c in session.calls if c.path.startswith("assets")]


# --------------------------------------------------------------------------- accounts, Library


def test_list_accounts_text():
    data = {
        EMAIL: {**ACCOUNTS[EMAIL], "videoLimitUntil": "2026-10-23T14:12:00.000Z"},
        OTHER: {"email": OTHER, "health": "Account jane@gmail.com: Meta asks for a security check"},
    }
    ctx, _, _ = make_ctx([("GET", "accounts", data)])
    items = run(HANDLERS["list_accounts"], ctx, {})
    body = outs(items, "text")[0].value
    assert "2 Muse account(s) connected, 1 healthy" in body and "plan Free" in body and "3% of the weekly allowance used" in body
    assert "video jobs skip it until 2026-10-23T14:12:00.000Z" in body and "needs attention" in body
    assert vars_of(items)["healthy_emails"] == [EMAIL]


def test_get_account_live_usage():
    data = {
        **ACCOUNTS[EMAIL],
        "session": "signed-in",
        "quota": {"tier": "HATCH_FREE", "percentUsed": 7, "resetsAt": "2026-10-19T01:13:18.000Z", "quotaStatus": "SUFFICIENT"},
    }
    ctx, session, _ = make_ctx([("GET", "accounts/", data), ("GET", "accounts", ACCOUNTS)])
    items = run(HANDLERS["get_account"], ctx, {})
    assert session.calls[-1].path == f"accounts/{EMAIL}" and session.calls[-1].timeout == 90
    assert vars_of(items) == {"plan": "Free", "percent_used": 7, "resets_at": "2026-10-19T01:13:18.000Z"}


def test_reads_need_an_email_with_several_accounts():
    ctx, _, _ = make_ctx([("GET", "accounts", {EMAIL: {}, OTHER: {}})])
    with pytest.raises(UseapiError, match="'email' is required"):
        run(HANDLERS["list_assets"], ctx, {})
    ctx, _, _ = make_ctx([("GET", "accounts", {})])
    with pytest.raises(UseapiError, match="Connect one first"):
        run(HANDLERS["list_chats"], ctx, {})


def test_upload_file_from_dify_file():
    ctx, session, _ = make_ctx([("POST", "assets", upload_ok())])
    items = run(HANDLERS["upload_file"], ctx, {"file": FakeFile()})
    assert session.calls[0].query == {} and session.calls[0].data == b"img"
    assert vars_of(items) == {"asset_id": IMG, "email": EMAIL}
    assert "Uploaded the image" in outs(items, "text")[0].value


@pytest.mark.parametrize("params,error", [({}, "Give a file"), ({"url": "http://example.com/a.jpg"}, "public https URL")])
def test_upload_file_needs_a_file_or_https_url(params, error):
    ctx, _, _ = make_ctx()
    with pytest.raises(UseapiError, match=error):
        run(HANDLERS["upload_file"], ctx, params)


def test_get_asset_as_pdf():
    ctx, session, _ = make_ctx([("GET", "assets/", FakeResponse(200, content=b"%PDF", headers={"Content-Type": "application/pdf"}))])
    doc = f"user:12345-email:{HEX}-document:notes.md"
    items = run(HANDLERS["get_asset"], ctx, {"asset_id": doc, "format": "pdf"})
    assert session.calls[0].query == {"format": "pdf"}
    assert outs(items, "blob")[0].meta == {"mime_type": "application/pdf", "filename": "muse-file.pdf"}


def test_list_assets_paging():
    data = {"email": EMAIL, "assets": [{**IMG_FILE, "name": "fox.webp", "updated": "2026-10-12"}], "cursor": "next-1", "partial": True}
    ctx, _, _ = make_ctx([("GET", "assets", data)])
    items = run(HANDLERS["list_assets"], ctx, {"email": EMAIL})
    body = outs(items, "text")[0].value
    assert "cursor = next-1" in body and "may be incomplete" in body and IMG2 in body
    assert vars_of(items) == {"asset_ids": [IMG2], "cursor": "next-1"}


# --------------------------------------------------------------------------- chat


def test_chat_waits_for_the_reply_to_this_message():
    stale = chat_record(status="completed", reply=None)  # the read right after sending: nothing after our message yet
    running = chat_record(status="running", reply="Working on it")
    finished = chat_record(status="completed", reply="Here it is.", files=[IMG_FILE])
    ctx, session, clock = make_ctx(
        [
            ("POST", "chats", {"chatId": CHAT, "email": EMAIL, "messageId": "m-1"}),
            ("GET", "chats/", [stale, running, finished]),
            ("GET", "assets/", FakeResponse(200, content=b"webp", headers={"Content-Type": "image/webp"})),
        ]
    )
    items = run(HANDLERS["chat"], ctx, {"message": "make an image", "files": f"{IMG}\nworkspace/your_files/report.pdf"})
    post = session.calls[0]
    assert post.body == {"message": "make an image", "files": [IMG, "workspace/your_files/report.pdf"], "email": EMAIL}
    assert clock.sleeps == [10, 10]
    body = outs(items, "text")[0].value
    assert body.startswith("Here it is.") and IMG2 in body and "earlier answer" not in body
    variables = vars_of(items)
    assert variables["chat_id"] == CHAT and variables["status"] == "completed" and variables["asset_ids"] == [IMG2]
    assert outs(items, "blob")[0].meta["filename"] == "muse-chat.webp"


def test_chat_continues_on_the_chats_account():
    ctx, session, _ = make_ctx(
        [("POST", "assets", upload_ok()), ("POST", "chats/", {"chatId": CHAT, "messageId": "m-1"}), ("GET", "chats/", chat_record())]
    )
    run(HANDLERS["chat"], ctx, {"message": "use image_1", "chat_id": CHAT, "upload_files": [FakeFile()], "return_file": False})
    assert session.calls[0].path == "assets" and session.calls[0].query == {"email": EMAIL}
    assert session.calls[1].path == f"chats/{CHAT}/messages" and session.calls[1].body == {"message": "use image_1", "files": [IMG]}


def test_chat_stops_at_a_permission_request():
    waiting = chat_record(status="running", reply="I need to open a site.", approvals=[APPROVAL])
    ctx, _, clock = make_ctx([("POST", "chats", {"chatId": CHAT, "messageId": "m-1"}), ("GET", "chats/", waiting)])
    items = run(HANDLERS["chat"], ctx, {"message": "make an image"})
    body = outs(items, "text")[0].value
    assert "asks for permission" in body and "87c8850c" in body and "answer_approval" in body and "allow_once, allow_always, deny" in body
    assert vars_of(items)["status"] == "waiting_for_approval" and vars_of(items)["approval_ids"] == ["87c8850c"]
    assert clock.sleeps == []


def test_chat_still_running_after_the_wait():
    ctx, _, clock = make_ctx([("POST", "chats", {"chatId": CHAT, "messageId": "m-1"}), ("GET", "chats/", chat_record(status="running"))])
    items = run(HANDLERS["chat"], ctx, {"message": "make an image", "max_wait_seconds": 30})
    assert sum(clock.sleeps) == 30
    assert "still working" in outs(items, "text")[0].value and "Do not send the message again" in outs(items, "text")[0].value


def test_chat_shows_quick_replies():
    widgets = [{"widgetId": "w1", "kind": "option", "text": "Pick one", "options": ["Cats", "Dogs"]}]
    ctx, _, _ = make_ctx([("POST", "chats", {"chatId": CHAT, "messageId": "m-1"}), ("GET", "chats/", chat_record(widgets=widgets))])
    items = run(HANDLERS["chat"], ctx, {"message": "make an image"})
    assert "quick replies: Cats / Dogs" in outs(items, "text")[0].value


def test_get_chat_wait_follows_until_idle():
    ctx, _, clock = make_ctx([("GET", "chats/", [chat_record(status="running"), chat_record(status="completed")])])
    items = run(HANDLERS["get_chat"], ctx, {"chat_id": CHAT, "wait": True, "return_file": False})
    assert clock.sleeps == [10] and vars_of(items)["status"] == "completed"


def test_answer_approval_resolves_the_only_request_and_follows():
    before = chat_record(status="running", reply="I need to open a site.", approvals=[APPROVAL])
    after = chat_record(status="completed", reply="I need to open a site.")
    after["messages"].append({"messageId": "a-9", "role": "assistant", "text": "Done, I read the site.", "files": []})
    ctx, session, _ = make_ctx(
        [
            ("POST", "chats/", {"chatId": CHAT, "approvalId": "87c8850c", "decision": "allow_once", "status": "approved"}),
            ("GET", "chats/", [before, before, after]),
        ]
    )
    items = run(HANDLERS["answer_approval"], ctx, {"chat_id": CHAT, "decision": "allow_once"})
    post = next(c for c in session.calls if c.method == "POST")
    assert post.path == f"chats/{CHAT}/approvals/87c8850c" and post.body == {"decision": "allow_once"}
    assert outs(items, "text")[0].value.startswith("Done, I read the site.")


def test_answer_approval_needs_an_id_with_several_requests():
    two = chat_record(status="running", approvals=[APPROVAL, {**APPROVAL, "approvalId": "b2"}])
    ctx, session, _ = make_ctx([("GET", "chats/", two)])
    with pytest.raises(UseapiError, match="'approval_id' is required"):
        run(HANDLERS["answer_approval"], ctx, {"chat_id": CHAT, "decision": "deny"})
    assert not [c for c in session.calls if c.method == "POST"]
    with pytest.raises(UseapiError, match="allow_once, allow_always or deny"):
        run(HANDLERS["answer_approval"], ctx, {"chat_id": CHAT, "decision": "approve"})


def test_list_chats_and_jobs_text():
    chats = {
        "email": EMAIL,
        "chats": [{"chatId": CHAT, "title": "Sea story", "status": "completed", "updated": "2026-10-12"}],
        "cursor": None,
    }
    ctx, _, _ = make_ctx([("GET", "chats", chats)])
    items = run(HANDLERS["list_chats"], ctx, {"email": EMAIL})
    assert "Sea story [completed]" in outs(items, "text")[0].value and vars_of(items) == {"chat_ids": [CHAT], "cursor": None}
    jobs = {
        "running": [{"jobid": JOB, "email": EMAIL, "type": "video", "created": "2026"}],
        "accounts": {EMAIL: {"running": 1, "maxJobs": 3}},
    }
    ctx, _, _ = make_ctx([("GET", "jobs", jobs)])
    items = run(HANDLERS["list_jobs"], ctx, {})
    assert "1 of 3 job slots" in outs(items, "text")[0].value


def test_runner_drops_empty_values():
    ctx, _, _ = make_ctx([("GET", "chats", {"email": EMAIL, "chats": [], "cursor": None})])
    items = list(runner.outputs(ctx, "list_chats", {"email": EMAIL}))
    assert items[0].kind == "text"
    assert not [o for o in items if o.kind == "var"]  # an empty list and a null cursor are left out


def test_chat_without_message_id_finds_the_message_by_text():
    previous = chat_record(status="completed", reply=None)
    previous["messages"] = previous["messages"][:2]  # the read right after sending: only the earlier turn, already completed
    finished = chat_record(status="completed", reply="New answer.")
    ctx, _, clock = make_ctx([("POST", "chats/", {"chatId": CHAT, "messageId": None}), ("GET", "chats/", [previous, finished])])
    items = run(HANDLERS["chat"], ctx, {"message": "make an image", "chat_id": CHAT, "return_file": False})
    assert clock.sleeps == [10]
    assert outs(items, "text")[0].value.startswith("New answer.") and "earlier answer" not in outs(items, "text")[0].value


def test_answer_approval_waits_for_muse_to_go_on():
    before = chat_record(status="completed", reply="I need to open a site.", approvals=[APPROVAL])
    resolved = chat_record(status="completed", reply="I need to open a site.")  # answered, nothing new yet
    ctx, _, clock = make_ctx([("POST", "chats/", {"status": "approved"}), ("GET", "chats/", [before, resolved])])
    items = run(HANDLERS["answer_approval"], ctx, {"chat_id": CHAT, "decision": "deny", "max_wait_seconds": 20, "return_file": False})
    assert sum(clock.sleeps) == 20  # kept reading until the wait ran out: no new message after the answer
    assert "Get Muse chat" in outs(items, "text")[0].value
