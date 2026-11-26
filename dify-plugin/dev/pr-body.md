# Plugin Submission

## Plugin information

- **Author**: useapi
- **Plugin name**: muse_useapi
- **Version**: 0.1.0
- **Source repository**: https://github.com/useapi/muse-api/tree/main/dify-plugin
- **Contact**: support@useapi.net

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

New tool plugin for Muse, Meta's AI agent at muse.ai, through the useapi.net Muse API. 13 tools:

- Generate video: one video of about 10 seconds with sound, from text, from a photo (a line written in quotes is spoken, a talking photo), or from a video to edit, with up to 9 input images, 3 videos and 3 audio files.
- Generate image: text to image, or image to image from up to 9 input images (combine, edit, restore and colorize old photos).
- The Muse agent: start or continue a chat, read it, answer its permission requests, list chats.
- Jobs, uploads, the Muse Library (list and download files) and accounts with their weekly usage.

Results come back as text, JSON, workflow variables and Dify files. The interface is in English, Simplified Chinese, Japanese and Brazilian Portuguese.

useapi.net is not affiliated with Meta; this is stated in the plugin description, README and PRIVACY.md. The plugin itself is free. It requires external services, disclosed in the description and README: a useapi.net subscription ($15/month) and the user's own Muse account at muse.ai (the free plan works; Muse is available in the US, Canada, Japan, Singapore and Australia, as of November 25, 2026). The README shows Meta's Muse plans (Free, Power $20/month, Maximum $100/month) and their weekly allowances, with the source and date.

## Risk level

- [ ] Low risk
- [x] Medium risk
- [ ] High risk

Medium: the plugin sends user content (prompts, chat messages and uploaded images, videos and audio) to an external service, performs write actions there (generations and chat turns that use the user's weekly Muse allowance, uploads, answers to the agent's permission requests), and downloads the generated files. Every request, downloads included, goes to one fixed HTTPS API, `api.useapi.net`, declared in `manifest.yaml` `network.domains`.

## Required checks

- [x] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the Plugin Developer Agreement.
- [x] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

- Network: every call goes only to `https://api.useapi.net/v1/muse`, the one domain in `manifest.yaml` `network.domains`. Only inert types (images, video, audio, PDF, plain text and Markdown) are attached as they are; HTML is attached as plain text (.html.txt) and SVG or unknown types as opaque .bin files. Finished files are downloaded from the same API (`GET /assets/{assetId}`), which streams them from the user's Muse account; the plugin never fetches from another host and does not follow redirects. The `useapi.net` and `muse.ai` hits in the static scan are links inside error messages (the setup docs, and muse.ai where the user signs in to clear an account check), not requests.
- File upload: image, video and audio parameters accept a Dify file the user selected. It is sent to the API as the raw body of the upload endpoint (JPEG, PNG, WebP, MP4, MOV, WebM, MP3, WAV, M4A, OGG, up to 50 MB). The upload tool can instead pass a public https URL, which the API downloads. No filesystem access.
- Credentials: the useapi.net token is a `secret-input` and is sent only in the `Authorization` header to `api.useapi.net`. Error messages never include it (the "token" in error strings is the word, plus a link to the setup page). The Muse account password is never handled by the plugin: accounts are added at useapi.net.
- Agent permission requests: the Muse agent asks before some actions, such as sharing information with a website. The plugin never answers on its own: "Answer a Muse permission request" sends only the decision the user or the Dify agent gives, and its description tells the agent to ask the user first.
- The "payment" and "charged" matches in the financial check, if any, are the 402 Payment Required error message and the subscription price disclosure. The plugin performs no payments or transfers.
- Every request has a timeout (60 s; 90 s for the live account read; 120 to 150 s for job submission and chat messages; 300 s for uploads and downloads). Waits are capped at 420 s, under Dify's 600 s plugin limit: long jobs return a job id and the user checks it with "Get job status".
- The plugin stores nothing; see PRIVACY.md.

## Local validation

```
python -m pytest                                    # 193 passed: every tool with a mocked HTTP layer, SDK loading of all YAML and tool classes, i18n completeness, agent safety
ruff check .                                        # All checks passed
python dev/routing_check.py                         # 8/8 read-only endpoints answer 401 to a fake token (routes exist)
dify plugin package ./dify-plugin                   # plugin packaged successfully
python3 validator/validate-difypkg.py <pkg>         # dify-marketplace-toolkit: 0 blocking failures (review warnings explained in Security and privacy notes)
python3 validator/test-plugin-install.py -d <dir>   # Plugin test result: success
```

## Reviewer notes

This is a tool plugin, not a model provider or a plain gateway. It does not resell a model API:

- It drives the user's own Muse account at muse.ai, Meta's consumer agent, and runs on that account's plan (the free plan works). Jobs and chats use the account's weekly Muse allowance; nothing is billed per call.
- What it covers is not in an official API. As of November 26, 2026, Meta's Model API sells the Muse Image model ($0.01 per image, dev.meta.ai pricing page) and text models, but it has no video generation and no API for the Muse agent at muse.ai, where the videos, the talking photos and the agent's research and documents are made.
- Users can connect several Muse accounts. With the email left empty, useapi.net sends each job to a healthy account with allowance left and a free job slot, and skips an account that reached Muse's 24-hour video limit, so the weekly allowance of every account adds up.

Brand: "Muse" is a Meta product name. The label names the provider ("Meta Muse by useapi.net"), the description says "Third-party API by useapi.net, not affiliated with Meta", and the icon is our own paper-boat logo, not Meta's. We already publish `useapi/notebooklm_useapi` (merged in #3410) and `useapi/google_flow_useapi` (merged in #3959) with the same approach.

Testing: 0.1.0 was tested on Dify Cloud on 2026-11-26 in an agent app (gpt-5): local package install, credential validation (Save checks the token with GET /accounts), "List Muse accounts" (2 accounts, both OK), "Generate image" (completed, the image attached as a file) and "Generate video" (completed, a 4.9 MB MP4 attached as a file). The handler code was also run directly against the live API the same day (image 42 s, video 63 s), and 200 offline tests pass. Note: in the Legacy Agent "Debug & Preview" pane, Dify's front end logged `TypeError: Cannot use 'in' operator to search for 'transferMethod'` while rendering a returned file; the app Logs show the files attached correctly. Not tested on a self-hosted Community Edition instance.
