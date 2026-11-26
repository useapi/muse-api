# Submitting to the Dify Marketplace

Local notes, not shipped in the package (`dev/` is in `.difyignore`). The rules are the ones checked for `useapi/notebooklm_useapi` (merged in #3410) and `useapi/google_flow_useapi` (merged in #3959) against `langgenius/dify-plugins` (README, `docs/plugin-submission-requirements.md`, `docs/marketplace-curation-policy.md`, `.github/pull_request_template.md`, `.github/workflows/pre-check-plugin.yaml`) and `langgenius/dify-marketplace-toolkit` (the validators the PR check runs). Re-check them before submitting.

## What the Marketplace requires

- **One file per PR**: the `.difypkg` only, at `useapi/muse_useapi/muse_useapi-0.1.0.difypkg`.
- **Public source repository**: `https://github.com/useapi/muse-api` (folder `dify-plugin/`), in `manifest.yaml` `repo` and linked in `README.md`. Push the folder before the PR, because the README links to it.
- **Manifest**: author, name, version, type `plugin`, icon in `_assets/`, privacy, repo, contact email, en_US label and description, runner, and 1 to 3 `tags` from Dify's fixed list (`videos`, `image`, the same as the accepted Google Flow plugin; `agent` is on the marketplace list but not in the SDK's provider tag enum, so it is left out).
- **PRIVACY.md** in the package, referenced by `privacy:`. Present.
- **README in English**; localized READMEs in `readme/README_<locale>.md` (zh_Hans, ja_JP, pt_BR).
- **Dependencies**: `dify_plugin==0.10.2`, `requests==2.34.2`, pinned, no git or URL installs.
- **Paid services**: the plugin is free; the useapi.net subscription and the user's Muse plan are disclosed in the description and README.
- **Brands**: "Muse" is a Meta product. The label says "by useapi.net", the description says "not affiliated with Meta", and the icon is our own logo.
- **No duplicates**: search the Marketplace for "Muse" and "Meta" before submitting (a Marketplace search for "muse" on 2026-11-25 found no Muse plugin; re-check).

## Media download decision

Muse files are not on a public CDN: the API streams them from the user's Muse workspace with `GET /assets/{assetId}` on `api.useapi.net`, with the same token. So the plugin needs one network domain only, and the download refuses redirects. Each attached file is capped at 150 MB (Muse uploads are at most 50 MB, a generated video is about 5 MB); "Attach the files" (`return_file`) turns downloading off and leaves the asset ids.

## Async mode and chat

The API's sync mode holds a job for about 100 seconds, then answers 202. The plugin submits jobs with `async: true` and polls `GET /jobs/{jobid}` every 10 seconds, up to "Maximum wait" (120 s for images, 180 s for videos by default, 420 max), then returns the `jobid`.

The chat tools do not use the SSE stream (`GET /chats/{chatId}/stream`): they send the message, then read `GET /chats/{chatId}?limit=200` every 10 seconds until an agent message follows the message sent (by `messageId`, or by its text when the API returns none) and the chat is no longer `running`, or a permission request waits. Answering a permission request reads the chat first (to know the last message), answers, then waits for a new agent message. Each read opens a connection to Muse on our side, which is why the interval is 10 seconds.

## Steps

1. Review and commit `dify-plugin/` in `useapi/muse-api`, add a "Use in Dify" section to the repo README, then push.
2. Rebuild the package from the pushed tree (`dify-plugin-linux-amd64` from https://github.com/langgenius/dify-plugin-daemon/releases):
   ```bash
   dify plugin package ./dify-plugin -o muse_useapi-0.1.0.difypkg
   ```
3. Attach it to a GitHub release (`gh release create dify-v0.1.0 muse_useapi-0.1.0.difypkg`), since the READMEs point to Releases for manual install.
4. Install it on Dify Cloud (Plugins > Install plugin > Local package file) with a token that has a Muse account, and run List Muse accounts, Generate image and Generate video (one each: they use the weekly Muse allowance), then fill the Testing paragraph in `pr-body.md`.
5. Re-check Meta's Model API price (`TODO(owner)` in `pr-body.md`).
6. Fork `langgenius/dify-plugins`, add the single file `useapi/muse_useapi/muse_useapi-0.1.0.difypkg`, push to the fork.
7. Open the PR to `main`:
   - Title: `Add Meta Muse by useapi.net tool plugin (useapi/muse_useapi) 0.1.0`
   - Body: `dev/pr-body.md`.
   - Risk: Medium.
8. Wait for `pre-check-plugin`. Once merged, the plugin is listed automatically.
9. Updates later: bump `version` in `manifest.yaml` and `USER_AGENT` in `useapi_muse/client.py` (a test checks they match), add `CHANGELOG.md` notes, and send a PR with only the new `.difypkg`.

## Local checks to repeat before submitting

```bash
python -m pytest
ruff check .
python dev/routing_check.py      # read-only routes answer 401 with a fake token; never a real token, never a generation
python3 validator/validate-difypkg.py <pkg> --pr-body-file dev/pr-body.md --output-dir <dir>   # in dify-marketplace-toolkit
INSTALL_METHOD=serverless SERVERLESS_PORT=8080 SERVERLESS_HOST=127.0.0.1 python3 validator/test-plugin-install.py -d <unpacked pkg>
```

The validator's remaining warnings are expected and explained in the PR body: "token" appears as a word in docs and error messages, `useapi.net` documentation links and `muse.ai` (where a user clears an account check) are found by the domain scan, and "payment" matches the 402 message.
