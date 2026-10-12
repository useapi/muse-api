---
name: muse-video
description: Make AI images and 10-second videos with sound using Meta's Muse agent (muse.ai) through the useapi.net Muse API, on the user's own Muse account (the free plan works). Text to image, combining up to 9 photos into one picture, editing an image, restoring and colorizing an old photo, image to video with spoken dialogue (make a photo talk), and video to video such as replacing a person in a clip. Files chain by assetId with no re-upload. Downloads the .webp or .mp4. Use when the user asks for a Muse or Meta Muse image or video, a talking photo, an old photo restored or animated, a face or person swapped in a video, or a short AI video with dialogue from the command line. Needs curl, jq and a USEAPI_TOKEN environment variable.
license: MIT
compatibility: Needs bash, curl, jq and network access to api.useapi.net. Requires a useapi.net API token (USEAPI_TOKEN) and a Muse account (muse.ai, free or paid) added to useapi.net with the Muse setup.
metadata:
  author: useapi.net
  homepage: https://github.com/useapi/muse-api
---

# Images and 10-second videos with Meta Muse via the useapi.net Muse API

These scripts call the [useapi.net Muse API](https://useapi.net/docs/api-muse-v1), a third-party REST API that drives the user's own account on Muse (muse.ai), Meta's AI agent. useapi.net is not affiliated with Meta. Every job uses part of the account's **weekly** Muse allowance. Every script is in `scripts/` next to this file. Run them with bash.

## Before you start

1. `USEAPI_TOKEN` must be set. If it is missing, ask the user for their useapi.net API token (setup: https://useapi.net/docs/start-here/setup-useapi). Their Muse account must already be added (https://useapi.net/docs/start-here/setup-muse). **Never print the token, echo it, or write it to a file.**
2. `USEAPI_EMAIL` is optional: the added Muse account to use. Leave it unset and the API picks a healthy account with allowance left. All inputs of one job must be on the same account, and a job runs on the account that holds its inputs, so set it when the user has several accounts and you upload files.
3. `curl` and `jq` must be installed.

## Fastest path: one command

```bash
scripts/image.sh "<prompt>" [image_1=<assetId> ...]
scripts/video.sh "<prompt>" [image_1=<assetId> video_1=<assetId> ...]
```

Each prints progress on stderr and the saved file path on stdout (`.webp` for images, `.mp4` for videos), with the job record next to it as `.json`. The new file's `assetId` is logged and is in `.result.assets[0].assetId` of that `.json`: pass it to the next job. `OUT_DIR` sets the folder, default the current one. An image takes 20 to 60 seconds, a video 60 to 140. Run videos in the background (in Claude Code, `run_in_background`) or with a timeout of at least 10 minutes, and do not start a second copy while one runs.

```bash
# Text to image: say the aspect ratio in the prompt
scripts/image.sh "In exactly 16:9 aspect ratio (landscape), a cinematic photo of a vintage motorcycle on wet cobblestones at night, fog, 35mm film."

# Make a photo talk: upload it, animate it, put the line in quotes
IMG=$(scripts/upload.sh grandma.jpg)
scripts/video.sh "Animate image_1 with the same portrait frame: she looks up at the camera, smiles and says softly: \"You came back.\" Keep her face exactly as in image_1." image_1="$IMG"
```

## Chaining: pass assetIds, never re-upload

Every file Muse makes stays in the account's Muse workspace, so its `assetId` goes straight into the next job as `image_N` or `video_N`. Upload only the user's own files, with `upload.sh` (free, no allowance, the same file always gets the same id).

```bash
BIKE=$(scripts/upload.sh bike.jpg); RIDER=$(scripts/upload.sh rider.jpg); BEACH=$(scripts/upload.sh beach.jpg)
PIC=$(scripts/image.sh "In exactly 16:9 aspect ratio (landscape), the woman from image_2 riding the motorcycle from image_1 through the surf of the beach in image_3. Use the beach from image_3 exactly as photographed. Keep her face and the motorcycle exactly as in the images." \
  image_1="$BIKE" image_2="$RIDER" image_3="$BEACH")
PIC_ID=$(jq -r '.result.assets[0].assetId' "${PIC%.*}.json")
CLIP=$(scripts/video.sh "Animate image_1 in exactly 16:9 aspect ratio: she rides through the waves and shouts: \"Nothing beats this view!\" Keep her face and the motorcycle exactly as in image_1." image_1="$PIC_ID")
CLIP_ID=$(jq -r '.result.assets[0].assetId' "${CLIP%.*}.json")
NEW=$(scripts/upload.sh other-woman.jpg)
scripts/video.sh "Edit video_1: replace the rider with the woman from image_1, keep everything else the same. Instead of the original line she shouts: \"Catch me if you can!\" Keep the 16:9 frame." video_1="$CLIP_ID" image_1="$NEW"
```

## Costs (the weekly Muse allowance)

Muse meters each account per week, as a whole percent used. `scripts/account.sh` reads it live: `quota.tier` (`HATCH_FREE` is the free plan), `quota.percentUsed`, `quota.resetsAt`. On the free plan, in useapi.net's tests:

| Request | Used of the week (free plan) |
|---|---|
| A video (`video.sh`, `generate.sh video`) | 2 to 3 percent |
| An image (`image.sh`, `generate.sh image`) | 0 to 1 percent |
| Upload, download, reading a job or the account | nothing |
| A failed job (`503`, `403` refusal) | nothing made |

So one free account makes roughly 30 to 50 videos or several hundred images a week. Paid Muse plans (Power, Maximum) have larger allowances. When it runs out, a job on that account answers `412` until `resetsAt`. useapi.net itself is a flat $15/month subscription with no per-image or per-video charge. Tell the user the cost before more than two or three videos.

## Writing prompts that work

- **There are no parameters for model, aspect ratio, resolution or length.** Say it in the prompt.
- **Aspect ratio: write `in exactly 16:9 aspect ratio`** (or 9:16, 1:1, 4:5, 3:4, 21:9 ...). "Cinematic 16:9 landscape photo" once came back 3:2. Image to video keeps the start image's shape unless the prompt asks for another ratio.
- **Every video is about 10 seconds at about 720p, with sound.** Asking for 5 seconds still gives 10; asking for 1080p or 4K adds no detail.
- **Spoken lines go in quotes**: `she says softly: "..."`. One or two short sentences.
- **Name the inputs** in the prompt: `the woman from image_2 riding the motorcycle from image_1`. A prompt that names an input you did not pass answers `400`.
- **Say what must stay the same**: "keep her face exactly as in image_1", "use the beach from image_3 exactly as photographed: same position, not mirrored or redrawn".
- **Animate**: `Animate image_1 ...` makes a clip that starts from that picture. **Edit a video**: `Edit video_1: replace the rider with the woman from image_1, keep everything else the same`.
- **Restore an old photo**: list what to fix (scratches, fading, grain, colorize) and insist on "the same framing, crop and aspect ratio as image_1".
- `result.text` is Muse's own last message, e.g. "Done. 10 seconds, 16:9 landscape". Pass it on to the user.

## Step by step (for more control)

```bash
JOB=$(scripts/generate.sh video "Animate image_1: ..." image_1="$IMG")   # prints the job id, sent once
scripts/wait-job.sh "$JOB" > job.json                                     # polls every 10 s, prints the final record
scripts/download.sh job.json ./out                                        # prints the saved .mp4 path
jq -r '.result.assets[0].assetId' job.json                                # the clip, for the next job
```

| Script | Interface |
|---|---|
| `image.sh "<prompt>" [image_1..9=<assetId>]` | generate + wait + download an image, prints the `.webp` path |
| `video.sh "<prompt>" [image_1..9= video_1..3= audio_1..3=]` | generate + wait + download a video, prints the `.mp4` path |
| `upload.sh <file>` | upload jpeg/png/webp/mp4/mov/webm/mp3/wav/m4a/ogg up to 8.6 MB, prints the `assetId` |
| `generate.sh image\|video "<prompt>" [key=value ...]` | also `replyUrl`, `replyRef`; prints the job id |
| `wait-job.sh <jobid>` | polls until done, prints the job record; exits 1 on a failed job with a hint |
| `download.sh <job.json\|-\|assetId> [OUT_DIR] [NAME]` | saves `muse_<type>_<time>.<webp\|mp4>`, prints the path |
| `account.sh [email]` | the account's plan and weekly usage, read live (no email: every account, as last read) |

Every option: https://useapi.net/docs/api-muse-v1

Files are never deleted by the API: they stay in the account's Muse workspace and can be downloaded again by `assetId`. Job records are kept for 7 days (then `410`).

## Timeouts and resuming without paying twice

`generate.sh`, `image.sh` and `video.sh` send each job **once and never retry it**: a job resent after an unclear failure would use the allowance twice. If a run is interrupted after `job j...-bot:muse` was logged, do **not** run it again. Resume with the job id:

```bash
scripts/wait-job.sh "<jobid>" > job.json && scripts/download.sh job.json
```

Reading jobs, reading the account, uploading and downloading cost nothing, so those scripts retry network errors and `5xx` answers on their own and are safe to re-run.

## Errors

Every failed request or failed job prints the API's error and a one-line hint:

- `400`: a parameter was rejected (the message names it), an input of the wrong type (`video_1` given an image), inputs on different accounts, or the prompt names an input that was not passed. Nothing was used.
- `401`: wrong token. `404`: the account is not added, or the file is no longer in the Muse workspace. `410`: the job is older than 7 days.
- `403` on a job: **Muse refused** on content grounds (its own words are in the message), or asked for a confirmation. Running the same prompt again will not help: rephrase or change the inputs. `403` on a request: the id belongs to another API token.
- `412`: the account's weekly allowance is used up. Use another account (`account.sh`) or wait for `resetsAt`.
- `429`: the account is running its `maxJobs` (default 2), or Muse is limiting it for about a minute. Nothing was made: send once more after a minute. Never loop on it.
- `503`: **nothing was made**: Muse could not be reached, or Muse failed this time and said so ("the video worker glitched out before it rendered anything"). Running the same request again is safe and usually works.
- `502`: Muse made a file the API could not read. Do not resubmit automatically: tell the user and report the job id to useapi.net support.
- `504`: Muse did not finish in time, but **it may have made the file**. Check `GET /jobs/<jobid>?history=true` and ask the user before running it again.
- `596`: the Muse account needs attention: Meta wants a security check, or the password changed. The user signs in at https://muse.ai, then re-adds the account: https://useapi.net/docs/start-here/setup-muse

## After it finishes

Tell the user the file path(s), what Muse said (`result.text`), and for videos the length (about 10 s). If you read the account, say how much of the week is used (`quota.percentUsed`) and when it resets. Mention that each result's `assetId` can feed the next job with no re-upload.
