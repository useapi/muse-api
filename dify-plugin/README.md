# Meta Muse by useapi.net

**Author:** [useapi](https://useapi.net/?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) · **Version:** 0.1.0 · **Type:** tool · **Source:** https://github.com/useapi/muse-api/tree/main/dify-plugin · **Contact:** support@useapi.net

Use Muse, Meta's AI agent at [muse.ai](https://muse.ai), from Dify [workflows, chatflows](https://docs.dify.ai/en/cloud/use-dify/build/workflow-chatflow) and [agents](https://docs.dify.ai/en/cloud/use-dify/build/new-agent/overview). Make videos of about 10 seconds with sound from text, bring a photo to life and let the person in it speak a line, edit a video with people from your images, make images from text or from up to 9 input images, and chat with the Muse agent, which researches the web, writes documents and code, and makes files for you. Images, videos and documents come back as Dify files.

**It runs on your own Muse account, and the free plan works.** Connect several Muse accounts and leave the email empty: useapi.net sends each new job to a healthy account with allowance left and a free job slot, so the weekly allowance of every account adds up. See [Several Muse accounts](#several-muse-accounts).

> This plugin calls the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) by useapi.net, a third-party API. It is not made by, affiliated with or endorsed by Meta. You need a useapi.net subscription ($15/month, covers every useapi.net API) and a Muse account at muse.ai. Muse is available in the US, Canada, Japan, Singapore and Australia (as of November 25, 2026), so create the account in one of them; once it is added, you can call the API from anywhere.

## Muse plans and the weekly allowance

Muse meters each account weekly. Jobs and chats use the allowance of the account they run on; uploads and downloads use none.

| Muse plan | Price | Weekly allowance |
|---|---|---|
| Free | $0 | not published |
| Power | $20/month | 500 million Muse tokens |
| Maximum | $100/month | 3 billion Muse tokens |

Source: Meta, [About Muse subscriptions](https://www.meta.com/help/subscriptions/1021145227643680/), November 2026, as listed in the useapi.net [Muse setup](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin#usage-limits). Availability can differ by region. On the free plan, a video used 2 to 3 percent of the weekly allowance in useapi.net's tests and an image 0 to 1 percent; Meta does not publish per-job costs. **Get Muse account usage** shows how much is used and when it resets. The table shows the Muse plan only. The useapi.net subscription ($15/month) is separate.

## Quick start

1. **Get a useapi.net API token.** Subscribe and copy your token: [Setup useapi.net](https://useapi.net/docs/start-here/setup-useapi?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin).
2. **Connect a Muse account.** Follow [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin). The account needs email and password sign-in, finished onboarding at muse.ai (including Meta's age check) and one image made there. Use it only for the API, with no other automation tools on it.
3. **Install and authorize the plugin, then make a video.** Install it from the [Dify Marketplace](https://marketplace.dify.ai/plugins/useapi/muse_useapi), or upload the `.difypkg` from the [GitHub releases](https://github.com/useapi/muse-api/releases) under Plugins > Install plugin > Local package file. In Tools, open "Meta Muse by useapi.net", click Authorize, paste the token and save. Then add **Generate video** to a workflow with the prompt `A paper boat floating on a calm pond at sunrise, a frog on the bank says "Bon voyage!"`, set the aspect ratio to 16:9 and run it. The `.mp4` comes back as a file.

### Credentials

| Credential | Required | What it is |
|---|:-:|---|
| `useapi.net API token` | Yes | Your token from step 1. Stored by Dify as a secret. |
| `Default Muse account email` | No | Leave empty so useapi.net picks the account. Set it only to pin every tool to one Muse account. |

Saving the credentials makes one check, `GET /accounts`, which confirms the token works and that at least one Muse account is connected. It does not call Muse.

### Connection requirements

The plugin connects only to `https://api.useapi.net/v1/muse`, with the token in an `Authorization: Bearer` header. Finished files are downloaded from the same API (`GET /assets/{assetId}`), which streams them from your Muse account. A self-hosted Dify needs outbound HTTPS to `api.useapi.net`. No proxy, webhook or inbound connection is required.

## Several Muse accounts

Each useapi.net subscription can add 3 Muse accounts. Add each one the same way as the first, with [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin). **List Muse accounts** then shows each account's health, plan and weekly usage, and **List running jobs** shows how many job slots each one uses.

**How the account is picked.** When the email is empty and a job has no input files, useapi.net sends it to a healthy account with allowance left and a free job slot (`maxJobs`, 10 by default). A video job also skips an account that reached Muse's video limit for the last 24 hours. An account whose weekly allowance is used up is skipped until it resets.

**Inputs pin the account.** A file you uploaded, or one Muse made, lives on one Muse account, and all inputs of one job or chat must be on the same account. So a request with input asset ids runs on their account. Files you attach to a tool are uploaded to the account of the other ids in that request. A chat stays on the account it started on: continue it with its `chat_id`.

**When to set an email.** Leave it empty for the best spread. Set the default email in the credentials to pin every tool to one account, or set the email on one tool to send just that call there.

## Tools

13 tools. Asset ids look like `user:12345-email:<hex>-video:<name>.mp4`; pass them between nodes as variables. Endpoints are relative to `https://api.useapi.net/v1/muse`.

| Tool | Label | Endpoint |
|---|---|---|
| `generate_image` | Generate image | `POST /jobs/image` |
| `generate_video` | Generate video | `POST /jobs/video` |
| `get_job` | Get job status | `GET /jobs/{jobid}` |
| `list_jobs` | List running jobs | `GET /jobs` |
| `chat` | Muse chat | `POST /chats`, `POST /chats/{chatId}/messages`, `GET /chats/{chatId}` |
| `get_chat` | Get Muse chat | `GET /chats/{chatId}` |
| `answer_approval` | Answer a Muse permission request | `POST /chats/{chatId}/approvals/{approvalId}` |
| `list_chats` | List Muse chats | `GET /chats` |
| `upload_file` | Upload a file to Muse | `POST /assets` |
| `list_assets` | List Muse Library | `GET /assets` |
| `get_asset` | Download a Muse file | `GET /assets/{assetId}` |
| `list_accounts` | List Muse accounts | `GET /accounts` |
| `get_account` | Get Muse account usage | `GET /accounts/{email}` |

### What Muse makes

Muse is an agent, not a fixed generator: there are no model, resolution or length settings. Describe what you want in the prompt.

| Tool | Result | Inputs |
|---|---|---|
| Generate image | One WebP image, about 2 to 2.5 megapixels. Text to image; combine inputs into one scene, edit an image, or restore and colorize an old photo. | Up to 9 images, named `image_1` to `image_9` in the prompt |
| Generate video | One MP4 of about 10 seconds, about 720p, with sound. Text to video; image to video, where a line written in quotes is spoken (a talking photo); video to video, for example swapping a person for someone from `image_1`. | Up to 9 images, 3 videos and 3 audio files, named `image_N`, `video_N`, `audio_N` |
| Muse chat | Muse's answer, plus any files it made (images, videos, documents, web apps) | Asset ids and workspace paths, named `image_1`, `video_1`, `audio_1`, `file_1` in order |

- **Aspect ratio.** The "Aspect ratio" option adds `In exactly <ratio> aspect ratio` to the prompt, the wording Muse follows best. Images: 1:1, 16:9, 9:16, 3:2, 2:3, 4:3, 3:4, 5:4, 4:5 or 21:9. Videos: 16:9, 9:16 or 3:4. An image-to-video job keeps the start image's shape unless you ask for a ratio.
- **Inputs.** Each input takes an asset id (from Upload, a job result or the Library) or a Dify file, which the plugin uploads first: JPEG, PNG or WebP images, MP4, MOV or WebM videos, and MP3, WAV, M4A or OGG audio, up to 50 MB each. Ids come first, then files, in the order given.
- **Repeated prompts.** Muse remembers what an account already made, across chats. Sending the same prompt again on the same account can be refused with `409` and nothing made. Vary the prompt for each new image or video, or run it on another account.

### Outputs

- **text**: a readable summary with the asset ids and Muse's own message, or what to do next. This is what an agent reads.
- **json**: the API response; for the chat tools, the latest answer's messages, permission requests and browsers (widget HTML left out).
- **files**: the finished `.webp`, `.mp4` or other file. Turn off "Attach the files" to skip them. Files over 150 MB are not attached.
- **variables**: `jobid`, `status`, `asset_ids` and `reply` from the generation tools; `chat_id`, `status`, `reply`, `asset_ids` and `approval_ids` from the chat tools; `asset_id` from Upload; `emails` and `healthy_emails` from List Muse accounts.

## Usage examples

### Workflow: a talking photo in two nodes

```
[Start: photo (file), line (text)]
        |
[Meta Muse > Generate image]      prompt = Restore and colorize the old photograph image_1. Keep the same person,
                                           framing and portrait aspect ratio.
                                  image_files = {{Start.photo}}
        |
[Meta Muse > Generate video]      prompt = Animate image_1: she looks up at the camera, smiles and says:
                                           "{{Start.line}}" Keep her face exactly as in image_1.
                                  images = {{Generate image.asset_ids}}
                                  Maximum wait = 420
        |
[End: video = {{Generate video.files}}, id = {{Generate video.asset_ids}}]
```

The restored image needs no download or upload to be used again: its asset id goes straight into the video. Both jobs run on the account the photo was uploaded to. If the video is still running after the wait, add a **Get job status** node with `jobid = {{Generate video.jobid}}`.

### Agent: a creative assistant with the Muse agent

Create an Agent app and add Muse chat, Get Muse chat, Answer a Muse permission request, Generate image, Generate video and Get job status. Use instructions like:

```
You help the user make images, short videos and documents with Meta Muse.
- For one image or one clip, use Generate image or Generate video. For research, writing or a mix of
  files, use Muse chat, and continue the same chat with its chat_id.
- When Muse asks for permission, tell the user what it wants to do and answer only after the user agrees.
- If a tool says a job or answer is still running, never send it again: call Get job status or
  Get Muse chat with wait=true.
- Muse refuses to repeat a request the account already made: change the wording for each new attempt.
```

Then ask, for example: "Research three facts about paper boats, write them as a short script, and make a 9:16 video of the first one."

## Waiting and limits

- **Dify's 600-second limit.** A Dify plugin call ends after 600 seconds (`PLUGIN_MAX_EXECUTION_TIMEOUT`). So the generation tools submit the job, poll it every 10 seconds and return after 120 seconds for images and 180 for videos by default. If the job is not done, they return its `jobid`: call **Get job status** with it. In a workflow you can raise "Maximum wait" up to 420 seconds. The job keeps running after the call returns, and job records are kept for 7 days.
- **Timing.** In useapi.net's tests an image took 20 to 60 seconds and a video 60 to 140. A chat answer depends on what Muse does; a running answer comes back with its `chat_id` for **Get Muse chat**.
- **Job slots.** Each Muse account runs at most `maxJobs` jobs at once (10 by default, 1 to 50, set at useapi.net). Chats and uploads take no slot.
- **Video limit.** Besides the weekly allowance, Muse limits the videos an account makes over the last 24 hours. Video jobs then skip that account for an hour; image jobs still work.
- **Permission requests.** Before some actions, such as sharing information with a website, the agent asks. The chat returns `waiting_for_approval` with an `approval_id`: answer with **Answer a Muse permission request** before it expires. The plugin answers once (`allow_once`) or denies (`deny`); to allow a site for good, answer "always" in muse.ai.
- **Attached files.** Images, video, audio, PDF, plain text and Markdown are attached as they are. An HTML document is attached as plain text (`.html.txt`); use **Download a Muse file** with the PDF format for a PDF version. SVG and unknown types are attached as opaque `.bin` files.

## Troubleshooting

| Code | What it means | What to do |
|---|---|---|
| 400 | The request is wrong, for example the prompt names `image_2` but no second image was given, or no Muse account is connected. | Change what the message says, or connect an account with [Setup Muse](https://useapi.net/docs/start-here/setup-muse). |
| 401 | The useapi.net token is wrong. | Check the token in the plugin's credentials. |
| 402 | The useapi.net subscription is not active. | Renew it: [subscription](https://useapi.net/docs/subscription). |
| 403 | Muse refused to make it (its own words are in the message), Meta has switched off video for the account in its region, or the id belongs to another API token. Or Muse asked for permission. | Change the prompt or the inputs: sending the same one again will not help. For video, use another account. If Muse asked for permission, run it as a Muse chat and answer with `answer_approval`. |
| 404 | The account is not connected, or the job, chat or file no longer exists. | Connect the account with [Setup Muse](https://useapi.net/docs/start-here/setup-muse). |
| 409 | Muse says the account already made this request, so nothing was made. Or a permission request was already answered. | Change the prompt, or run it on another account. |
| 410 | The job has expired. | Job records are kept for 7 days. |
| 412 | The weekly Muse allowance is used up on the account (or on every account). | Wait for the reset (see **Get Muse account usage**), or connect another account. |
| 429 | Every job slot is busy, Muse is limiting the account for a minute, or the account reached Muse's 24-hour video limit. | Retry after the time in the message, or leave the email empty so another account takes it. |
| 502, 504 | Muse answered with an error, or did not finish in time. The job may still have made the file. | Check **Get job status** or **List Muse chats** before running it again. |
| 503 | Muse could not be reached, or failed to make it this time. | Run it again: the same prompt usually works on the next try. |
| 596 | The account needs attention: Meta asks for a security check, or Muse refused to sign it in again. Or Muse took the account's computer away. | Sign in once at muse.ai, then add the account again with [Setup Muse](https://useapi.net/docs/start-here/setup-muse). If Muse took the account's computer away, ask Muse support to restore it, then add the account again. |

## What it costs

- The plugin is free.
- useapi.net: $15/month, for every useapi.net API.
- Meta: your own Muse plan, the free one included. Jobs and chats use its weekly allowance.

## Privacy

The plugin sends requests only to `api.useapi.net` and stores nothing. See [PRIVACY.md](./PRIVACY.md) and the useapi.net [Terms and Privacy Policy](https://useapi.net/docs/legal?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin).

## Support

- API reference: https://useapi.net/docs/api-muse-v1
- Examples (Node.js, Python, n8n, an agent skill and this plugin's source): https://github.com/useapi/muse-api
- Email support@useapi.net, or ask on [Discord](https://discord.gg/w28uK3cnmF) or [Telegram](https://t.me/use_api).

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).

## Development

The tool YAML and Python stubs are generated from `dev/specs.py`, the single source of the parameters and their four UI languages (English, Simplified Chinese, Japanese, Brazilian Portuguese). Parameter names and limits follow the published API catalog, `https://api.useapi.net/v1/muse/models`.

```bash
python dev/gen_tools.py                 # writes tools/*.yaml, tools/*.py and the provider YAML
python -m pytest                        # every tool against a mocked HTTP layer
python dev/routing_check.py             # live 401 check of every read-only endpoint with a fake token
dify plugin package . -o muse_useapi-0.1.0.difypkg
```

`dev/` and `tests/` are left out of the package by `.difyignore`.
