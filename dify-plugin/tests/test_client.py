"""Error mapping and transport behaviour of the HTTP client."""

import pytest
import requests

from fakes import FakeResponse, FakeSession
from useapi_muse.client import USER_AGENT, Client, FileTooLarge, UseapiError, describe_error, filename_from

ASSET = "user:12345-email:6578616d706c6540676d61696c2e636f6d-video:media-generation-x-0-4322afa2.mp4"


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (
            400,
            {"error": "Please configure at least one account at https://useapi.net/docs/api-muse-v1/post-muse-accounts", "code": 400},
            "No Muse account is connected",
        ),
        (400, {"error": "The prompt names image_2, but 'image_2' was not provided in the request body", "code": 400}, "names an input"),
        (400, {"error": "Parameter image_1 must be a image asset, this one is a video", "code": 400}, "Details: Parameter image_1"),
        (401, {"error": "useapi.net ⁝ Unauthorized", "code": 401}, "rejected the API token"),
        (402, {"error": "no subscription", "code": 402}, "subscription is not active"),
        (403, {"error": "This asset id does not belong to this API token", "code": 403}, "another useapi.net API token"),
        (
            403,
            {
                "error": "Muse keeps refusing this prompt on account example@gmail.com, so it was not sent and nothing was made.",
                "code": 403,
            },
            "Change the prompt, or run it on another Muse account",
        ),
        (
            403,
            {"error": "Meta has switched off video for account example@gmail.com in its country or region", "code": 403},
            "Image jobs still work",
        ),
        (
            403,
            {
                "error": "Muse keeps refusing this prompt on every account that could take it, so it was not sent and nothing was made.",
                "code": 403,
            },
            "on every account that could take it",
        ),
        (
            403,
            {
                "error": "Meta has switched off video for all 2 accounts in their country or region, so video jobs cannot run. Image jobs still work.",
                "code": 403,
            },
            "Connect an account where video works",
        ),
        (
            403,
            {"jobid": "j1", "status": "failed", "error": {"code": 403, "message": "I can't make that."}},
            "Details: I can't make that.",
        ),
        (404, {"error": "Account example@gmail.com is not configured", "code": 404}, "Connect it first"),
        (404, {"error": "Job not found", "code": 404}, "Not found (404). Details: Job not found"),
        (409, {"error": "This approval is no longer waiting (status approved, decision allow_once)", "code": 409}, "already answered"),
        (
            409,
            {"jobid": "j1", "status": "failed", "error": {"code": 409, "message": "Already delivered earlier"}},
            "already made this request",
        ),
        (410, {"error": "Job has expired", "code": 410}, "kept for 7 days"),
        (412, {"error": "All 2 healthy accounts have used up their Muse allowance.", "code": 412}, "weekly Muse allowance is used up"),
        (413, {"error": "File must be at most 52428800 bytes", "code": 413}, "up to 50 MB"),
        (422, {"error": "Muse could not convert this file (HTTP 400)", "code": 422}, "could not do this"),
        (
            429,
            {
                "error": "Account example@gmail.com reached Muse's video limit for the last 24 hours.",
                "code": 429,
                "retryAt": "2026-10-23T14:12:00.000Z",
            },
            "Retry after 2026-10-23T14:12:00.000Z",
        ),
        (
            429,
            {
                "error": "All 3 accounts reached Muse's video limit for the last 24 hours. Video jobs try the first one again after 2026-10-23T14:12:00.000Z",
                "code": 429,
                "retryAt": "2026-10-23T14:12:00.000Z",
            },
            "Every connected Muse account reached",
        ),
        (
            429,
            {"error": "All 1 accounts are running their maximum number of jobs (maxJobs), please retry shortly", "code": 429},
            "job slot",
        ),
        (429, {"error": "Muse is limiting requests on account example@gmail.com right now.", "code": 429}, "Retry in about a minute"),
        (502, {"error": "Muse did not accept the message (HTTP 400). Please retry", "code": 502}, "uses the allowance again"),
        (503, {"error": "Could not connect to the Muse workspace", "code": 503}, "Retry shortly"),
        (504, {"error": "The connection to Muse dropped while sending", "code": 504}, "check before sending it again"),
        (596, {"error": "Account example@gmail.com: Meta asks for a security check", "code": 596}, "https://muse.ai"),
        (596, {"error": "No healthy Muse account configured. Check GET /accounts", "code": 596}, "No connected Muse account is healthy"),
        (500, None, "useapi.net side"),
    ],
)
def test_describe_error(status, body, expected):
    assert expected in describe_error(status, body)


def test_never_advises_a_reset():
    """Muse's refusals are memory rules the account keeps: a reset is never the advice (owner decision, 2026-11-12)."""
    import re

    advice = re.compile(r"reset (the|this|your|it)\b|/reset", re.IGNORECASE)
    for status in (400, 403, 404, 409, 412, 429, 502, 503, 504, 596):
        assert not advice.search(describe_error(status, {"error": "x", "code": status}))


def test_retry_after_header_wins():
    assert "Retry after 30 seconds" in describe_error(429, {"error": "maxJobs", "retryAt": "2026"}, {"Retry-After": "30"})
    assert "Retry after 2026" in describe_error(429, {"error": "x", "retryAt": "2026"}, {})


def test_error_raised_with_status():
    session = FakeSession([("GET", "accounts", FakeResponse(401, {"error": "useapi.net ⁝ Unauthorized", "code": 401}))])
    with pytest.raises(UseapiError) as e:
        Client("bad", session=session).request("GET", "accounts")
    assert e.value.status == 401


def test_headers_and_user_agent():
    session = FakeSession()
    Client("user:1-x", session=session).request("GET", "accounts")
    headers = session.calls[0].headers
    assert headers["Authorization"] == "Bearer user:1-x"
    assert headers["User-Agent"] == USER_AGENT == "dify-plugin-muse-useapi/0.1.0"
    assert session.calls[0].host == "api.useapi.net"


def test_missing_token():
    with pytest.raises(UseapiError, match="token is missing"):
        Client("  ")


class Boom:
    def __init__(self, exc):
        self.exc = exc

    def request(self, *a, **k):
        raise self.exc


def test_timeout_and_network_errors():
    with pytest.raises(UseapiError, match="within 60 seconds"):
        Client("t", session=Boom(requests.Timeout())).request("GET", "accounts")
    with pytest.raises(UseapiError, match="Could not reach api.useapi.net"):
        Client("t", session=Boom(requests.ConnectionError())).request("GET", "accounts")


def test_empty_params_are_dropped():
    session = FakeSession()
    Client("t", session=session).request("GET", "assets", params={"email": None, "type": ""})
    assert session.calls[0].query == {}


def test_download_asset_from_the_api_with_the_token():
    session = FakeSession(
        [
            (
                "GET",
                "assets/",
                FakeResponse(
                    200,
                    content=b"mp4bytes",
                    headers={"Content-Type": "video/mp4", "Content-Disposition": 'inline; filename="media-generation-x.mp4"'},
                ),
            )
        ]
    )
    blob, mime, name = Client("t", session=session).download_asset(ASSET)
    call = session.calls[0]
    assert (blob, mime, name) == (b"mp4bytes", "video/mp4", "media-generation-x.mp4")
    assert call.host == "api.useapi.net" and call.path == f"assets/{ASSET}"
    assert "%3A" in call.raw_path  # the id is URL-encoded in the path
    assert call.headers["Authorization"] == "Bearer t"


def test_download_errors_redirects_and_size():
    session = FakeSession([("GET", "assets/", FakeResponse(404, {"error": "This file is no longer in the Muse workspace", "code": 404}))])
    with pytest.raises(UseapiError, match="no longer in the Muse workspace") as e:
        Client("t", session=session).download_asset(ASSET)
    assert e.value.status == 404
    session = FakeSession([("GET", "assets/", FakeResponse(302, content=b"", headers={"Location": "https://elsewhere.example/x"}))])
    with pytest.raises(UseapiError, match="302"):
        Client("t", session=session).download_asset(ASSET)
    session = FakeSession([("GET", "assets/", FakeResponse(200, content=b"x" * 100, headers={"Content-Type": "video/mp4"}))])
    with pytest.raises(FileTooLarge):
        Client("t", session=session).download_asset(ASSET, max_bytes=10)
    session = FakeSession(
        [("GET", "assets/", FakeResponse(200, content=b"x" * 100, headers={"Content-Length": "100", "Content-Type": "video/mp4"}))]
    )
    with pytest.raises(FileTooLarge):
        Client("t", session=session).download_asset(ASSET, max_bytes=10)


def test_download_stops_when_the_total_time_budget_is_spent():
    session = FakeSession([("GET", "assets/", FakeResponse(200, content=b"x" * 100, headers={"Content-Type": "video/mp4"}))])
    with pytest.raises(UseapiError, match="ran out of time"):
        Client("t", session=session).download_asset(ASSET, budget=-1)


@pytest.mark.parametrize(
    "header,name",
    [
        ('inline; filename="a.mp4"', "a.mp4"),
        ("attachment; filename=report.md", "report.md"),
        ("attachment; filename*=UTF-8''..%2Fx.pdf", "..%2Fx.pdf"),
        ('attachment; filename="../../etc/passwd"', "passwd"),
        (None, None),
    ],
)
def test_filename_from(header, name):
    assert filename_from(header) == name
