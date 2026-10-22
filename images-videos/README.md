# Meta Muse images and 10-second videos with sound — Muse API (Node.js & Python)

Full walkthrough: [How to Generate AI Videos and Images with the Meta Muse API](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) — October 12, 2026

Videos made with this API, on YouTube: [3 photos in, 1 talking video out: Meta Muse API from REST](https://youtube.com/shorts/v_7mREyFSWk) · [This old portrait just spoke: one API call (Meta Muse API, third-party)](https://youtube.com/shorts/GLHoINX_ozE) · [Replace the person in a video, keep everything else: Meta Muse API](https://youtube.com/shorts/XDCY1XIsd5Y)

Make images and 10-second videos with sound with Muse (muse.ai), Meta's AI agent, through the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) by [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api): three photos (a vintage BMW motorcycle, a red-haired rider, the beach below the Golden Gate Bridge) become one picture of her riding through the surf, the picture becomes a video in which she shouts a line, and a woman from a fourth photo then replaces her in that video. Along the way it makes two images from text, and restores and colorizes a hundred-year-old portrait that then looks up and speaks.

`images-videos.mjs` (Node.js) and `images-videos.py` (Python) are equivalent implementations of the tutorial's pipeline. Each reads every step from `prompts.json`, uploads the input photos with [`POST /assets`](https://useapi.net/docs/api-muse-v1/post-muse-assets?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), runs each generation as an async job (`async: true`), polls [`GET /jobs/{jobid}`](https://useapi.net/docs/api-muse-v1/get-muse-jobs-jobid?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) every 10 seconds, and downloads every image and MP4 with [`GET /assets/{assetId}`](https://useapi.net/docs/api-muse-v1/get-muse-assets-assetId?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

## Prerequisites

- [Node.js](https://nodejs.org) v21 or newer (no dependencies to install — uses built-in `fetch`), or [Python](https://www.python.org) 3.x (standard library only — no dependencies to install)
- A useapi.net [API token](https://useapi.net/docs/start-here/setup-useapi?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)
- A Muse account added through [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api). The free Muse plan works. Every job uses part of that account's weekly Muse allowance, which Muse reports as a whole percent used.

useapi.net charges a flat [$15/month](https://useapi.net/docs/subscription?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) for every API, with no per-image or per-video charge.

## Usage

```bash
node ./images-videos.mjs <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]
python3 ./images-videos.py <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]
```

`EMAIL` is the added Muse account. Every upload and every job is pinned to it, since all inputs of one job must live on the account that runs it. `PROMPTS_FILE` defaults to the `prompts.json` next to the script.

`--steps` runs only the named steps, plus the earlier steps they take a file from. For example `--steps portrait-video` restores the old photo and animates it (one image and one video), and `--steps swap` runs the whole motorcycle chain.

Before it spends anything, the script checks `prompts.json`, reads the account's plan and weekly usage with [`GET /accounts/{email}`](https://useapi.net/docs/api-muse-v1/get-muse-accounts-email?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), and stops if the account needs attention or Muse reports the allowance as used up. After each job it reads the account again and prints the percent used before and after.

## The pipeline

| Step | Endpoint | Inputs | Saved as |
|---|---|---|---|
| Upload the five photos | [POST /assets](https://useapi.net/docs/api-muse-v1/post-muse-assets?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | | (asset ids in the state file) |
| 1. `portrait`: text to image, 9:16 | [POST /jobs/image](https://useapi.net/docs/api-muse-v1/post-muse-jobs-image?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | | `portrait.webp` |
| 2. `bmw-noir`: text to image, exactly 16:9 | [POST /jobs/image](https://useapi.net/docs/api-muse-v1/post-muse-jobs-image?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | | `bmw-noir.webp` |
| 3. `beach-ride`: rider, motorcycle and beach in one picture | [POST /jobs/image](https://useapi.net/docs/api-muse-v1/post-muse-jobs-image?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | `image_1` bmw, `image_2` rider, `image_3` beach | `beach-ride.webp` |
| 4. `surf`: the picture as a 10-second video with a spoken line | [POST /jobs/video](https://useapi.net/docs/api-muse-v1/post-muse-jobs-video?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | `image_1` beach-ride | `surf.mp4` |
| 5. `restored`: restore and colorize the old portrait | [POST /jobs/image](https://useapi.net/docs/api-muse-v1/post-muse-jobs-image?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | `image_1` old-photo | `restored.webp` |
| 6. `portrait-video`: the portrait looks up and speaks | [POST /jobs/video](https://useapi.net/docs/api-muse-v1/post-muse-jobs-video?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | `image_1` restored | `portrait-video.mp4` |
| 7. `swap`: the woman from the fifth photo replaces the rider | [POST /jobs/video](https://useapi.net/docs/api-muse-v1/post-muse-jobs-video?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | `video_1` surf, `image_1` pink-hair | `swap.mp4` |

On the free plan a video uses 2 to 3 percent of the week and an image 0 to 1 percent. Our test run of the whole pipeline on October 12, 2026 went from 37 to 45 percent (the videos 3, 3 and 2 percent, every image 0) and took 7.5 minutes: the images 20 to 42 seconds each and the videos 72 to 116 seconds. Uploads use no allowance. See the tutorial's ["What it cost"](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#what-it-cost) table.

Steps 4, 6 and 7 take files Muse made in earlier steps by their `assetId`. Those files are already in the account's Muse workspace, so nothing is downloaded or uploaded in between.

## prompts.json

The tutorial's exact prompts.

- `inputs` — the photos to upload: `name` and `url`. The script downloads each one and uploads it with the MIME type the server reports. To use your own photos, change the URLs.
- `steps` — one job each, in order: `name` (the step's name and file name), `type` (`image` or `video`), `prompt`, and the inputs: `image_1`..`image_9`, plus `video_1`..`video_3` and `audio_1`..`audio_3` on video steps. Each input names an entry of `inputs` or an earlier step, which the script swaps for its `assetId`.

Muse has no model, aspect ratio, resolution or duration parameters: the prompt says them. Write the ratio as `in exactly 16:9 aspect ratio`. Every video is about 10 seconds at about 720p with sound, and lines in quotes are spoken. Name each input in the prompt (`the woman from image_2`); a prompt that names an input the step does not pass is caught before anything runs.

## Output

Everything lands in an `output/` folder in the current directory:

- the images (`.webp`) and the videos (`.mp4`),
- each job record (`<name>.json`, with `result.text`, Muse's own reply),
- `muse_state.json`, the asset ids of the uploads and of every finished step.

Run the script again and it continues where it stopped: finished steps are skipped (and downloaded again if their file is missing), and a job that was still running is picked up by its `jobid` instead of being sent again. To redo a step, delete its entry under `steps` in `muse_state.json`.

The API never deletes files: everything stays in the account's Muse workspace, where the muse.ai app shows it too, and every `assetId` in `muse_state.json` can be the input of your next job.

## Retries and errors

The script sends a job again only when nothing was made:

- a POST answered `429` because every `maxJobs` slot is busy (after `Retry-After`, 30 seconds), or `503`,
- a job that failed with `503` (Muse failed to make it this time and said so, for example "the video worker glitched out before it rendered anything"; in the tutorial the same request then worked), or with `429` (Muse was limiting the account; after a minute). Up to 3 tries.

Uploads are free and give the same `assetId` every time, so they are retried on any network error, `502` or `503`. If a job POST gets no answer at all, the script stops, because the job may have been accepted. Any other failure stops the script with the API's message:

| Error | What to do |
|---|---|
| `401` Unauthorized | Check the API token. |
| `404` Account is not configured | Add the account via [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), or pass the right `EMAIL`. |
| `403` Muse refused | Muse turned the prompt down, in its own words. Running it again will not help: change the prompt in `prompts.json`. |
| `412` allowance used up | The account's weekly Muse allowance is used up. `GET /accounts/{email}` shows `resetsAt`. |
| `502` | Muse made a file the API could not read. Report the `jobid` to support. |
| `504` | Muse did not finish in time but may have made the file. Check `GET /jobs/{jobid}?history=true` before running again. |
| `596` | The account needs attention: Meta asks for a security check, or the password changed. See [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#if-the-account-needs-attention). |

All codes are listed on [GET /jobs/{jobid}](https://useapi.net/docs/api-muse-v1/get-muse-jobs-jobid?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#error-codes).

---

Support: [Discord](https://discord.gg/w28uK3cnmF) · [Telegram](https://t.me/use_api) · [YouTube](https://www.youtube.com/@useapi-net)
