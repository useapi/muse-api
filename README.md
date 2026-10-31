# Meta Muse API examples (useapi.net): AI video, images and agent chat on muse.ai

Runnable examples for the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) by [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api): make images and 10-second videos with sound using Muse (muse.ai), Meta's AI agent, through a REST API that runs on your [Muse subscription](https://www.meta.com/help/subscriptions/1021145227643680/): Free, Power $20 or Maximum $100 a month (as of October 2026). Combine up to 9 photos into one picture, restore and colorize old photos, animate a still with spoken dialogue, and replace a person in a video. Every file Muse makes is an asset id the next job takes as an input, so edits chain with no downloads or re-uploads.

Demo on YouTube: [Meta Muse API Demo: Images, Talking Photos, Video with Sound, Chat & MCP (third-party, useapi.net)](https://www.youtube.com/watch?v=OMUGbfRIO5E)

| Example | What it does | Tutorial | Tutorial date |
|---|---|---|---|
| [`images-videos/`](./images-videos) | Three photos become one picture of a rider on a vintage motorcycle in the surf, the picture becomes a 10-second video in which she shouts a line, and a woman from a fourth photo replaces her in that video. Also two images from text, and a hundred-year-old portrait restored, colorized and brought to life. Node.js and Python | [How to Generate AI Videos and Images with the Meta Muse API](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 12, 2026 |
| [`narrated-short/`](./narrated-short) | Narrated 30-second Short from a topic: a chat writes the script as JSON, three 9:16 video jobs run at once with the same off-screen narrator speaking each line, and a last chat joins the clips with ffmpeg into one MP4. About 2 to 3 minutes per Short. Optional fixed voice through Muse text to speech. Node.js and Python | [Make a 30-second narrated Short](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#make-a-30-second-narrated-short-script-three-scenes-one-join) | October 18, 2026 |
| [`demo/`](./demo) | **Live chat app**: one self-contained HTML page that chats with the Muse agent through the API, with answers streamed live, files and cards, approvals, several live chats at once, workspace files and the agent's permissions. Open the [live demo](https://useapi.net/demos/muse/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) or open `demo/index.html` locally. Vanilla JS, no build | [Chat Streaming Guide](https://useapi.net/docs/api-muse-v1/chat-streaming-guide?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 12, 2026 |
| [`skills/muse-video/`](./skills/muse-video) | **Agent skill** for Claude Code, Codex and other coding agents: ask for an image or a clip and the agent makes it with Muse (text to image, photo compositing, old-photo restoration, talking photos, person swap in a video) and downloads the `.webp` or `.mp4`, never paying twice for a request. Install: `npx skills add useapi/muse-api --skill muse-video`. Bash, curl, jq | [SKILL.md](./skills/muse-video/SKILL.md) | October 12, 2026 |
| [`n8n/`](./n8n) | **n8n app**: upload an old photo, Muse restores and colorizes it, you pick or redo, then the person in it says your line in a 10-second video with sound. 1 or 2 takes, the real share of the week used on the result page, optional Google Drive save, and a Google Sheet batch mode. Core n8n nodes, no community nodes. Plus **narrated faceless Shorts** from a topic: a script page, one narrated 9:16 scene per part, joined and saved to Google Drive | [n8n template #20989](https://n8n.io/workflows/20989), [#21207](https://n8n.io/workflows/21207) | October 19, 2026 |
| [MCP server](#mcp-server) | **Hosted MCP server**: connect Claude Code, Cursor, VS Code or Windsurf to `https://api.useapi.net/v1/muse/mcp` and the assistant gets 37 tools for Muse images, videos, chat, files and permissions. Nothing to install or host | [MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 13, 2026 |

## Quick start

You need [Node.js](https://nodejs.org) v21 or newer **or** [Python](https://www.python.org) 3.x (no dependencies to install), a useapi.net [API token](https://useapi.net/docs/start-here/setup-useapi?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), and a Muse account (free or paid) added with the [Muse setup](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

```bash
git clone https://github.com/useapi/muse-api.git
cd muse-api/images-videos
node ./images-videos.mjs <API_TOKEN> <EMAIL>
# or, equivalently, with Python:
python3 ./images-videos.py <API_TOKEN> <EMAIL>
# just one image and one video (restore an old photo, then make it talk):
node ./images-videos.mjs <API_TOKEN> <EMAIL> --steps portrait-video
```

Each example's README lists its options. Every endpoint is documented in the [Muse API reference](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

## MCP server

useapi.net also runs a hosted [Model Context Protocol](https://modelcontextprotocol.io) server for Muse, so an AI assistant such as Claude Code, Cursor or VS Code Copilot can use Muse on your Muse subscription. It has 37 tools: generate images and videos, chat with the Muse agent, answer its permission requests, open a live view of its web browser, manage the account's Library and files, and reset the account. Each tool calls the Muse API, so the same rules, limits and allowance apply. Nothing needs to be installed or hosted.

- Endpoint: `https://api.useapi.net/v1/muse/mcp`
- Transport: Streamable HTTP
- Authorization: your useapi.net API token in the `Authorization: Bearer …` header, and at least one Muse account added with the [Muse setup](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)

Claude Code:

```bash
claude mcp add --transport http useapi-muse https://api.useapi.net/v1/muse/mcp --header "Authorization: Bearer YOUR_API_TOKEN"
```

Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "useapi-muse": {
      "url": "https://api.useapi.net/v1/muse/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

VS Code (`.vscode/mcp.json`):

```json
{
  "servers": {
    "useapi-muse": {
      "type": "http",
      "url": "https://api.useapi.net/v1/muse/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

Windsurf setup, a curl test, the full list of 37 tools and how long-running videos and chats are handled: [Muse MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

## Use with Claude Code

This repo is also a Claude Code plugin marketplace. The plugin adds the hosted Muse MCP server and the `muse-video` agent skill, and reads your token from the `USEAPI_TOKEN` environment variable, so set it before you start Claude Code:

```bash
export USEAPI_TOKEN=user:12345-...      # your useapi.net API token
```

Then, inside Claude Code:

```
/plugin marketplace add useapi/muse-api
/plugin install muse@useapi-muse
```

On Claude Code 2.1.275 or later, `/plugin install muse --marketplace useapi/muse-api` does both in one step. Run `/mcp` to check that `useapi-muse` is connected.

## Use with Gemini CLI

This repo is also a Gemini CLI extension with the same MCP server and the `muse-video` agent skill:

```bash
gemini extensions install https://github.com/useapi/muse-api
```

The install asks for your useapi.net API token and keeps it in the system keychain. Change it later with `gemini extensions config useapi-muse`, and check the connection with `gemini mcp list`. The `muse-video` skill's scripts read `USEAPI_TOKEN` from your shell, so export it as well if you use the skill.

## Articles and videos

- [Is There a Meta Muse Video API? Official API, Free Tools and a Hosted API (2026)](https://useapi.net/docs/articles/meta-muse-video-api?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)
- [How to Generate AI Videos and Images with the Meta Muse API](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)
- [Chinese-language tutorial (中文教程): AI images and videos with dialogue](https://useapi.net/docs/articles/muse-api-zh?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)
- YouTube: [Meta Muse API demo](https://www.youtube.com/watch?v=OMUGbfRIO5E), [a narrated 30-second Short made only with Muse API calls](https://www.youtube.com/shorts/1e8f7dHTkzs), [3 photos in, 1 talking video out](https://www.youtube.com/shorts/v_7mREyFSWk)

## Common questions

<!-- Official API figures in these answers, re-read 2026-10-20 (useapi.net/docs/api-muse-v1 sources): https://dev.meta.ai/docs/pricing-rate-limits (Muse Image $0.01 per image, no video model, no API for the Muse agent). Plans: https://www.meta.com/help/subscriptions/1021145227643680/ (Free, Power $20, Maximum $100 a month). Allowance figures: our tests on the free plan, 2026-10-12. -->

- **Is there a Meta Muse API?** Yes, through useapi.net: the useapi.net Muse API makes 10-second videos with sound and spoken dialogue, images, photo edits, person swaps and live chat with the Muse agent, on your Muse subscription. Meta sells no Muse video API: its [Model API](https://dev.meta.ai/docs/models) has the Muse Image model at $0.01 per image, but no video model and no API for the Muse agent (as of October 2026). [Is There a Meta Muse Video API?](https://useapi.net/docs/articles/meta-muse-video-api?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) compares the options.
- **How much does it cost?** Through useapi.net, an image or a video has no price of its own: it uses the weekly allowance of your Muse subscription, and the free plan works. In our tests on the free plan, a video used 2 to 3 percent of the week and an image 0 to 1 percent, and a paid plan gets a bigger allowance ([usage limits](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#usage-limits)). Meta's Model API sells no Muse video at any price (as of October 2026).
- **Is there a Muse API key?** Through useapi.net, one useapi.net [API token](https://useapi.net/docs/start-here/setup-useapi?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) is all the key you need, for the REST API and the [MCP server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) alike. Add your muse.ai email and password once with [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api), and we keep the account signed in, with no cookies to copy. Create the account in the US, Canada, [Japan](https://about.fb.com/ja/news/2026/10/muse-personal-ai-agent-launches-in-japan/) or [Singapore](https://about.fb.com/news/2026/10/muse-is-now-available-in-singapore-the-worlds-first-personal-ai-agent-built-for-everyone/), where Muse is available (as of October 2026), then call the API from anywhere.
- **How do I set the aspect ratio, length or resolution?** Through useapi.net, in the prompt: the Muse API has no parameters for them, because Muse picks its own model. Write `in exactly 16:9 aspect ratio`. Every video is about 10 seconds at about 720p, with sound, and lines written in quotes are spoken.
- **Can I use my own photos and videos?** Through useapi.net, yes: upload them with the Muse API (up to 50 MB each) and pass the `assetId` as `image_1`..`image_9`; video jobs also take `video_1`..`video_3` and `audio_1`..`audio_3`. All inputs of one job must be on the same Muse account, and uploads use none of the weekly allowance.

## 中文说明

这是 [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) 的 Muse API 示例代码。通过 REST API 调用 Meta 的 AI 助手 Muse（muse.ai），生成图片和带声音、带对白的 10 秒视频：多张照片合成一张图、老照片修复上色、让照片开口说话、视频换人。每个生成的文件都有一个 assetId，可以直接作为下一个任务的输入，无需下载再上传。

- 使用你的 Muse 订阅：免费版、Power 每月 20 美元或 Maximum 每月 100 美元（截至 2026 年 10 月），免费版即可。Muse 按周计算额度：免费版每个视频约占每周额度的 2% 到 3%，每张图片约 0% 到 1%。
- 没有画幅、时长、分辨率参数，全部写在提示词里，例如 `in exactly 16:9 aspect ratio`。视频约 10 秒、约 720p，引号里的台词会被说出来。
- 价格：useapi.net 每月 15 美元（含所有 API），不按图片或视频计费。
- 截至 2026 年 10 月，Muse 在美国、加拿大、[日本](https://about.fb.com/ja/news/2026/10/muse-personal-ai-agent-launches-in-japan/)和[新加坡](https://about.fb.com/news/2026/10/muse-is-now-available-in-singapore-the-worlds-first-personal-ai-agent-built-for-everyone/)开放，账号需要在这四个国家之一注册；绑定后可以在任何地方调用 API。
- MCP 服务器：在 Claude Code、Cursor、VS Code 或 Windsurf 中连接托管的 MCP 服务器 `https://api.useapi.net/v1/muse/mcp`（Streamable HTTP，`Authorization: Bearer` 填 useapi.net API token），即可获得 37 个工具：生成图片和视频、与 Muse 对话、处理权限请求、管理文件。说明：[Muse MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。
- useapi.net 是独立的第三方 API，与 Meta 无关联。

中文教程（多图合成、老照片修复、视频换人，含 curl 示例）：[如何通过 Muse API 用 Meta Muse 生成 AI 图片和带配音的视频](https://useapi.net/docs/articles/muse-api-zh?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。完整文档：[Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。

## About useapi.net

[useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) is a third-party REST API for AI services, not affiliated with or endorsed by Meta. The Muse API runs on your Muse subscription, so each image or video uses that account's weekly Muse allowance, with no price per image or video. One [$15/month subscription](https://useapi.net/docs/subscription?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) covers every useapi.net API and 3 Muse accounts.

Visit our [Discord Server](https://discord.gg/w28uK3cnmF) or [Telegram Channel](https://t.me/use_api) for any support questions and concerns.

We regularly post guides and tutorials on the [YouTube Channel](https://www.youtube.com/@useapi-net).

## License

The example code in this repository is released under the [MIT License](./LICENSE). It covers the example scripts only, not the useapi.net service or API.
