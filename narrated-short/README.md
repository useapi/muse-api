# Narrated 30-second Shorts from a topic with Meta Muse — Muse API (Node.js & Python)

Full walkthrough: **[Make a 30-second narrated Short (script, three scenes, one join)](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#make-a-30-second-narrated-short-script-three-scenes-one-join)** — October 18, 2026

Give it a topic and it makes a vertical 9:16 Short of 30 seconds with an off-screen narrator, using Muse (muse.ai), Meta's AI agent, through the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) by [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api). A Muse video is always about 10 seconds, so the Short is three clips joined into one:

1. A chat ([`POST /chats`](https://useapi.net/docs/api-muse-v1/post-muse-chats?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)) writes the script as JSON: a title, and per scene the narrator's line and a one-sentence shot.
2. One video job per scene ([`POST /jobs/video`](https://useapi.net/docs/api-muse-v1/post-muse-jobs-video?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), `async: true`), all at once. Every prompt carries the same narrator description and the scene's line in quotes, and Muse speaks the line word for word.
3. The jobs are polled with [`GET /jobs/{jobid}`](https://useapi.net/docs/api-muse-v1/get-muse-jobs-jobid?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) every 10 seconds.
4. One more chat gets the clips as `video_1`..`video_3` and joins them with ffmpeg in the account's Muse workspace.
5. The Short is downloaded with [`GET /assets/{assetId}`](https://useapi.net/docs/api-muse-v1/get-muse-assets-assetId?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) to `output/<topic>.mp4`.

`narrated-short.mjs` (Node.js) and `narrated-short.py` (Python) are equivalent. Every prompt is in `prompts.json`.

## Example output

[Watch the Short on YouTube](https://youtube.com/shorts/1e8f7dHTkzs) ([MP4](https://demo.useapi.net/discord-cdn-proxy/?https://cdn.discordapp.com/attachments/1239264794394234985/1561461244727398401/muse-narrated-short-tambora.mp4)) made from the topic `how a single volcano cooled the whole planet in 1816`: 720×1280, 30 seconds, three scenes about the 1815 eruption of Mount Tambora and the "year without a summer" that followed. The script Muse wrote for it:

| Scene | The narrator says | The shot |
|---|---|---|
| 1 | In April 1815, Mount Tambora in Indonesia erupted, the largest explosion in recorded history, blasting ash forty kilometers into the sky. | A massive volcanic eruption at dawn, with a towering ash column rising into the stratosphere above a dark island. |
| 2 | That ash veil circled Earth, blocking sunlight and dropping global temperatures, turning summer into winter across North America and Europe. | An animated globe wrapped in a gray haze as sunlight dims and frost spreads across continents. |
| 3 | 1816 became the Year Without a Summer: crops failed, snow fell in July, and famine spread as the planet shivered. | Snow falling over green farmland in summer, covering withered crops and empty village fields under a pale sun. |

## Prerequisites

- [Node.js](https://nodejs.org) v21 or newer (no dependencies to install, uses built-in `fetch`), or [Python](https://www.python.org) 3.8 or newer (standard library only)
- A useapi.net [API token](https://useapi.net/docs/start-here/setup-useapi?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)
- A Muse account added through [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api). The free Muse plan works. Every video uses part of that account's weekly Muse allowance.

useapi.net charges a flat [$15/month](https://useapi.net/docs/subscription?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) for every API, with no per-video charge.

## Usage

```bash
node ./narrated-short.mjs <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"] [--fixed-voice] [--tts-voice "<voice>"] [--prompts <file>]
python3 ./narrated-short.py <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"] [--fixed-voice] [--tts-voice "<voice>"] [--prompts <file>]
```

```bash
node ./narrated-short.mjs user:1234-abcdefhijklmnopqrstuv my@email.com "how a single volcano cooled the whole planet in 1816"
python3 ./narrated-short.py user:1234-abcdefhijklmnopqrstuv my@email.com "the forgotten history of the paperclip" --scenes 2
node ./narrated-short.mjs user:1234-abcdefhijklmnopqrstuv my@email.com "why octopuses are smarter than you think" \
  --narrator "Narration: one off-screen narrator only, the same voice throughout: a bright, curious young American female science host, quick pace. Nobody on screen speaks. No music."
```

| Argument | What it is |
|---|---|
| `API_TOKEN` | Your useapi.net API token, the first argument as in every example of this repo. |
| `EMAIL` | The Muse account to run on. Every chat and job is pinned to it, because the join chat must run on the account that holds the clips. |
| `TOPIC` | What the Short is about, in your own words. |
| `--scenes` | 1, 2 or 3 scenes of 10 seconds each (default 3). One chat takes up to 3 videos, so 3 is the most one join can take. With 1 scene there is no join. |
| `--narrator` | Your own narrator description, in place of the calm British documentary narrator of `prompts.json`. Keep "Nobody on screen speaks" in it so only the narrator talks. |
| `--fixed-voice` | Speak each line with Muse's text to speech first and lay it onto the clip. See [One voice for certain](#one-voice-for-certain---fixed-voice). |
| `--tts-voice` | The text to speech voice for `--fixed-voice`. Default: `Aria (avocado_v2:MAI_01)`. |
| `--prompts` | Another prompts file. Default: the `prompts.json` next to the script. |

Before it spends anything, the script reads the account's plan and weekly usage with [`GET /accounts/{email}`](https://useapi.net/docs/api-muse-v1/get-muse-accounts-email?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) and stops if the account needs attention or Muse reports the allowance as used up. At the end it prints the percent used before and after.

## Time and allowance

From the test run that made the Tambora Short on October 16, 2026:

| Step | Endpoint | Time |
|---|---|--:|
| Script as JSON | POST /chats | 11 s |
| Three clips, side by side | POST /jobs/video | 75, 75 and 87 s |
| Join | POST /chats | 20 s |

So a Short takes about 2 to 3 minutes. The chats use about 0 percent of the weekly allowance. That run was on a paid Muse plan, where the four videos of the test session moved the weekly reading by 2 points in all (Muse reports whole percents). On the free plan a video uses 2 to 3 percent of the week, so a three-scene Short costs about 6 to 9 percent there, and one free account makes roughly 11 to 16 Shorts a week.

## prompts.json

The prompts of the tutorial, word for word, with `{placeholders}` the script fills in:

- `script` — the script chat. `{topic}`, `{scenes}`, `{seconds}` (10 per scene) and `{shape}`, the JSON shape with one `{"line": string, "visual": string}` per scene. It asks for the JSON alone, no code fences, at most 25 words per line.
- `narrator` — the narrator description every scene shares. `--narrator` replaces it.
- `scene` — one video job: `{visual}`, `{narrator}` and `{line}`, which Muse speaks as written after `The narrator says exactly:`.
- `join` — the join chat: `{videos}` (`video_1, video_2, video_3`) and `{file}`, the file name in the workspace. It ends with `No public links.`, and with that line Muse did not stop to ask for permission in our tests.
- `tts` and `sceneWithVoice` — the text to speech chat and the video job of `--fixed-voice`.

Muse answered the script prompt with clean JSON for each of three topics we tried, in 11 to 29 seconds. The script still drops ```` ``` ```` fences and reads the outermost `{ … }`, and if the reply does not parse into the right number of scenes it asks once more.

## One voice for certain: --fixed-voice

The same narrator description gives the same kind of voice in every clip, not a locked one. In the Tambora clips the narrator's median pitch was 105 to 117 Hz, less than two semitones apart, but Muse voices each clip anew.

With `--fixed-voice` the script first asks Muse's text to speech for each line (one chat per line, about 20 seconds, voice `--tts-voice`), then passes that MP3 to the scene's video job as `audio_1`. Muse makes its clip and lays `audio_1` onto it with ffmpeg, and the job lists both files: the finished copy with `origin: "made"`, and Muse's raw clip with `origin: "generated"`, which carries a voice Muse made up. The script takes the `made` one, and stops if a job lists none, rather than join a clip with the wrong voice.

## Output

Everything lands in an `output/` folder in the current directory:

- `output/<topic>.mp4` — the Short,
- `output/<topic>/` — the script, each chat (`*.chat.json`) and each job record (`*.job.json`, with Muse's own reply in `result.text`), and `state.json`.

`state.json` holds the script, the chat ids, the job ids and the asset ids of the clips and the Short. Run the script again with the same topic and options and it continues where it stopped: a finished step is skipped, a job that was still running is picked up by its `jobid` and a chat by its `chatId`, instead of being sent again. To make a new Short on the same topic, move that folder away.

The clips and the Short also stay in the account's Muse workspace, where the muse.ai app shows them, and every asset id in `state.json` can be the input of your next job.

## Retries and errors

The script sends a request again only when the docs say nothing was made:

- a POST answered `429` (Muse is limiting the account, or every `maxJobs` slot is busy) or `503`, after `Retry-After` or 30 seconds, up to 10 times,
- a video job that failed with `503` (Muse failed to make it this time and said so) or `429` (after a minute), up to 3 tries.

A job that failed in any other way may have used allowance, so it is never sent again on its own: the script stops with the API's message and what to do. If a POST gets no answer at all, the script stops too, because the API may have taken it. Reading a job or a chat is free, so those reads are retried.

| Error | What to do |
|---|---|
| `401` Unauthorized | Check the API token. |
| `403` | Muse refused to make it, in its own words. Running it again will not help: change the topic or the prompt. |
| `404` Account is not configured | Add the account via [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), or pass the right `EMAIL`. |
| `412` | The weekly Muse allowance is used up. `GET /accounts/{email}` shows `resetsAt`. |
| `504` | Muse did not finish in time, or the connection dropped. It may still have made the file: check [`GET /jobs/{jobid}?history=true`](https://useapi.net/docs/api-muse-v1/get-muse-jobs-jobid?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) before you run it again. |
| `596` | The account needs attention, see [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api). |

Muse can ask permission before an action in a chat. The prompts are written so that it does not, but if it asks, the script denies anything about uploading, publishing or sharing, and allows anything else once (running ffmpeg, saving a file), with [`POST /chats/{chatId}/approvals/{approvalId}`](https://useapi.net/docs/api-muse-v1/post-muse-chats-chatId-approvals-approvalId?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

## MCP server

The same calls are tools on the hosted [Muse MCP server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), so an AI assistant in Claude Code, Cursor or VS Code can run the same steps: the script chat, the video jobs and the join.

---

useapi.net is a third-party API, not affiliated with or endorsed by Meta. It runs on a Muse account you own and add yourself.
