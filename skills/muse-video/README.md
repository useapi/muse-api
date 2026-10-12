# Meta Muse images and videos: an agent skill

An [Agent Skill](https://agentskills.io) that lets Claude Code, Codex and other coding agents make images and 10-second videos with sound using **Muse (muse.ai)**, Meta's AI agent: text to image, combining up to 9 photos into one picture, restoring and colorizing old photos, making a photo talk, and replacing a person in a video, then downloading the `.webp` or `.mp4`. Ask your agent "restore this old photo of my grandmother, then make her look up and say she missed me" and it runs the scripts in this folder.

It calls the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill) by [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill), a third-party REST API (not affiliated with Meta) that runs on your own Muse account. The free Muse plan works: each job uses part of the account's weekly Muse allowance, about 2 to 3 percent per video and 0 to 1 percent per image on the free plan.

## Install

With the [skills CLI](https://github.com/vercel-labs/skills) (asks which agents to install for):

```bash
npx skills add useapi/muse-api --skill muse-video
# add -g to install for your user instead of the current project
```

Or copy the folder yourself:

```bash
git clone https://github.com/useapi/muse-api.git
cp -r muse-api/skills/muse-video ~/.claude/skills/     # Claude Code, every project
cp -r muse-api/skills/muse-video .claude/skills/       # Claude Code, this project only
cp -r muse-api/skills/muse-video ~/.codex/skills/      # Codex
```

Then give the agent your token in the environment it runs in:

```bash
export USEAPI_TOKEN=user:12345-...      # your useapi.net API token
export USEAPI_EMAIL=you@example.com     # optional: which added Muse account to use
```

You need:

1. A useapi.net [API token](https://useapi.net/docs/start-here/setup-useapi?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill). One [$15/month subscription](https://useapi.net/docs/subscription?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill) covers every useapi.net API.
2. A Muse account (free or paid), added with the [Muse setup](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill).
3. `bash`, `curl` and [`jq`](https://jqlang.org/download/).

## Use it without an agent

The scripts work on their own too:

```bash
IMG=$(./scripts/upload.sh grandma.jpg)
./scripts/video.sh "Animate image_1 with the same portrait frame: she looks up, smiles and says softly: \"You came back.\" Keep her face exactly as in image_1." image_1="$IMG"
```

| Script | What it does |
|---|---|
| `scripts/image.sh` | Generate, wait and download an image in one command: prompt (and optional input images) in, `.webp` out |
| `scripts/video.sh` | The same for a 10-second video with sound: `.mp4` out |
| `scripts/upload.sh` | Upload your own image, video or audio file (up to 8.6 MB), print its `assetId` |
| `scripts/generate.sh` | Start an image or video job, print the job id |
| `scripts/wait-job.sh` | Poll the job until it is done, print the final record |
| `scripts/download.sh` | Download the finished file by job record or `assetId` |
| `scripts/account.sh` | Read the account's plan and weekly allowance used |

[`SKILL.md`](./SKILL.md) is what the agent reads: the options, allowance costs, prompting rules (aspect ratio, dialogue, what to keep the same), chaining by `assetId`, and what to do on each error without paying twice. The full API reference is at [useapi.net/docs/api-muse-v1](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=skill&utm_campaign=muse-skill). A worked pipeline is in [`images-videos/`](../../images-videos).
