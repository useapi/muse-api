"""The YAML files load in the Dify SDK, every tool has a handler and full i18n,
and the provider validates credentials."""

import re
from pathlib import Path

import pytest
import yaml
from dify_plugin.core.utils.class_loader import load_single_subclass_from_source
from dify_plugin.entities.tool import ToolProviderConfiguration
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.tool import Tool

from fakes import FakeResponse, FakeSession
from useapi_muse import runner
from useapi_muse.client import USER_AGENT, Client
from useapi_muse.handlers import HANDLERS, Ctx

ROOT = Path(__file__).resolve().parents[1]
LANGS = {"en_US", "zh_Hans", "ja_JP", "pt_BR"}
PROVIDER_FILE = ROOT / "provider/muse_useapi.yaml"
PROVIDER = yaml.safe_load(PROVIDER_FILE.read_text())
TOOL_FILES = [ROOT / p for p in PROVIDER["tools"]]
SHIPPED_TEXT = [
    *ROOT.glob("*.md"),
    *ROOT.glob("readme/*.md"),
    *ROOT.glob("tools/*.yaml"),
    ROOT / "manifest.yaml",
    PROVIDER_FILE,
]
# Dify's fixed marketplace tag list (langgenius/dify-plugins docs/marketplace-curation-policy.md), the ones that could fit.
DIFY_TAGS = {"videos", "image", "agent", "audio", "design", "entertainment", "productivity", "social", "utilities"}


def test_provider_loads_in_sdk():
    config = ToolProviderConfiguration(**yaml.safe_load(PROVIDER_FILE.read_text()))
    assert len(config.tools) == len(HANDLERS)
    assert {c.name for c in config.credentials_schema} == {"useapi_token", "email"}


def test_manifest_fields():
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    assert manifest["author"] == "useapi" and manifest["name"] == "muse_useapi"
    assert manifest["version"] == "0.1.0" and USER_AGENT.endswith("/" + manifest["version"])
    assert manifest["repo"] == "https://github.com/useapi/muse-api"
    assert manifest["network"]["domains"] == ["api.useapi.net"]
    assert manifest["privacy"] == "PRIVACY.md" and (ROOT / "PRIVACY.md").is_file()
    assert 1 <= len(manifest["tags"]) <= 3 and set(manifest["tags"]) <= DIFY_TAGS
    assert manifest["tags"] == PROVIDER["identity"]["tags"]
    assert set(manifest["label"]) == LANGS and set(manifest["description"]) == LANGS
    assert manifest["label"] == PROVIDER["identity"]["label"] and manifest["description"] == PROVIDER["identity"]["description"]
    for text in manifest["description"].values():
        assert "useapi.net" in text and "15" in text and "Muse" in text and "Meta" in text
    assert "not affiliated with Meta" in manifest["description"]["en_US"]
    assert (ROOT / "_assets" / manifest["icon"]).is_file()


def walk_i18n(node, where):
    if isinstance(node, dict):
        for key in ("label", "human_description", "human", "help", "placeholder"):
            if key in node and isinstance(node[key], dict):
                assert set(node[key]) == LANGS, (where, key, node[key])
                assert all(str(v).strip() for v in node[key].values()), (where, key)
        for key, value in node.items():
            walk_i18n(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            walk_i18n(value, f"{where}[{i}]")


@pytest.mark.parametrize("path", TOOL_FILES, ids=[p.stem for p in TOOL_FILES])
def test_tool_yaml(path):
    data = yaml.safe_load(path.read_text())
    walk_i18n(data, path.stem)
    assert data["identity"]["name"] in HANDLERS
    assert data["description"]["llm"].strip()
    for p in data.get("parameters", []):
        if p["form"] == "llm":
            assert p.get("llm_description"), (path.stem, p["name"])
        if p["type"] == "select":
            assert p["options"], (path.stem, p["name"])


@pytest.mark.parametrize("path", TOOL_FILES, ids=[p.stem for p in TOOL_FILES])
def test_tool_class_loads(path):
    data = yaml.safe_load(path.read_text())
    source = data["extra"]["python"]["source"]
    cls = load_single_subclass_from_source(module_name=source[:-3].replace("/", "."), script_path=str(ROOT / source), parent_type=Tool)
    assert issubclass(cls, Tool)


def test_handlers_read_only_declared_parameters():
    """Every p.get / P.<reader>(p, "name") in a handler is a parameter of some tool (no typo reaches Dify silently)."""
    source = (ROOT / "useapi_muse/handlers.py").read_text()
    read = set(re.findall(r'P\.\w+\(p, "([a-z_]+)"', source)) | set(re.findall(r'p\.get\("([a-z_]+)"\)', source))
    declared = {p["name"] for path in TOOL_FILES for p in yaml.safe_load(path.read_text()).get("parameters", [])}
    assert read <= declared, read - declared


def test_no_emoji_in_shipped_text():
    emoji = re.compile("[\U0001f300-\U0001faff☀-➿]")
    for path in SHIPPED_TEXT:
        assert not emoji.search(path.read_text(encoding="utf-8")), path


def test_wording():
    """'third-party', never 'unofficial'; Meta is named only to say we are not affiliated, never as the author."""
    for path in SHIPPED_TEXT:
        content = path.read_text(encoding="utf-8")
        assert "unofficial" not in content.lower(), path
        assert "official Meta" not in content, path
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    labels = [*manifest["label"].values(), *(yaml.safe_load(p.read_text())["identity"]["label"]["en_US"] for p in TOOL_FILES)]
    assert all("by Meta" not in label for label in labels)
    assert all("useapi.net" in label for label in manifest["label"].values())


def provider_with(routes, email=None):
    from provider.muse_useapi import MuseUseapiProvider

    session = FakeSession(routes)
    original = runner.make_context

    def fake_context(credentials):
        return Ctx(client=Client(credentials["useapi_token"], session=session), default_email=credentials.get("email") or None)

    runner.make_context = fake_context
    try:
        MuseUseapiProvider()._validate_credentials({"useapi_token": "user:1-x", "email": email})
    finally:
        runner.make_context = original
    return session


def test_credentials_ok():
    session = provider_with([("GET", "accounts", {"a@b.com": {"health": "OK"}})], email="a@b.com")
    assert session.calls[0].path == "accounts"


def test_credentials_bad_token():
    with pytest.raises(ToolProviderCredentialValidationError, match="rejected the API token"):
        provider_with([("GET", "accounts", FakeResponse(401, {"error": "useapi.net ⁝ Unauthorized", "code": 401}))])


def test_credentials_no_account():
    with pytest.raises(ToolProviderCredentialValidationError, match="no Muse account is connected"):
        provider_with([("GET", "accounts", {})])


def test_credentials_unknown_email():
    with pytest.raises(ToolProviderCredentialValidationError, match="not a connected Muse account"):
        provider_with([("GET", "accounts", {"a@b.com": {}})], email="other@b.com")


class FakeTool:
    class runtime:
        credentials = {"useapi_token": "t"}

    def create_text_message(self, text):
        return ("text", text)

    def create_json_message(self, obj):
        return ("json", obj)

    def create_variable_message(self, name, value):
        return ("var", name, value)

    def create_blob_message(self, blob, meta=None):
        return ("blob", meta)

    def create_link_message(self, link):
        return ("link", link)


def test_runner_converts_messages(monkeypatch):
    session = FakeSession([("GET", "accounts", {"a@b.com": {"health": "OK"}})])
    monkeypatch.setattr(runner, "make_context", lambda c: Ctx(client=Client("t", session=session)))
    messages = list(runner.invoke(FakeTool(), "list_accounts", {}))
    assert ("var", "emails", ["a@b.com"]) in messages
    assert messages[0][0] == "text" and "1 Muse account" in messages[0][1]


def load_tool(name):
    return load_single_subclass_from_source(module_name=f"tools.{name}", script_path=str(ROOT / f"tools/{name}.py"), parent_type=Tool)


def test_real_sdk_messages_for_a_generation(monkeypatch):
    """Run a generated Tool class through the SDK's own invoke() and message models."""
    from dify_plugin.entities.tool import ToolInvokeMessage

    asset = "user:1-email:61-video:media-generation-x.mp4"
    record = {
        "jobid": "j1",
        "type": "video",
        "status": "completed",
        "result": {"assets": [{"assetId": asset, "type": "video", "mime": "video/mp4", "bytes": 3}], "text": "Here it is."},
    }
    session = FakeSession(
        [
            ("POST", "jobs/video", record),
            ("GET", "assets/", FakeResponse(200, content=b"abc", headers={"Content-Type": "video/mp4"})),
        ]
    )
    monkeypatch.setattr(runner, "make_context", lambda c: Ctx(client=Client("t", session=session)))
    tool = load_tool("generate_video").from_credentials({"useapi_token": "t"})
    messages = list(tool.invoke({"prompt": "A boat", "wait": True}))
    assert all(isinstance(m, ToolInvokeMessage) for m in messages)
    kinds = [m.type for m in messages]
    assert kinds[0] == ToolInvokeMessage.MessageType.TEXT
    assert ToolInvokeMessage.MessageType.BLOB in kinds and ToolInvokeMessage.MessageType.JSON in kinds
    variables = {m.message.variable_name: m.message.variable_value for m in messages if m.type == ToolInvokeMessage.MessageType.VARIABLE}
    assert variables["jobid"] == "j1" and variables["asset_ids"] == [asset] and variables["reply"] == "Here it is."
    blob = next(m for m in messages if m.type == ToolInvokeMessage.MessageType.BLOB)
    assert blob.meta == {"mime_type": "video/mp4", "filename": "muse-video.mp4"}


def test_output_schema_matches_variables():
    """Every variable a tool can emit is declared in its output_schema."""
    source = (ROOT / "useapi_muse/handlers.py").read_text()
    emitted = set(re.findall(r'var\("([a-z_]+)"', source))
    declared = set()
    for path in TOOL_FILES:
        declared |= set((yaml.safe_load(path.read_text()).get("output_schema") or {}).get("properties", {}))
    assert emitted <= declared, emitted - declared


def test_generated_files_are_current():
    """tools/ and the provider YAML match dev/specs.py (re-run dev/gen_tools.py after editing the specs)."""
    import sys

    sys.path.insert(0, str(ROOT / "dev"))
    import gen_tools

    for spec in gen_tools.TOOLS:
        expected = gen_tools.HEADER + gen_tools.dump(gen_tools.tool_yaml(spec))
        assert (ROOT / f"tools/{spec['name']}.yaml").read_text(encoding="utf-8") == expected, spec["name"]
