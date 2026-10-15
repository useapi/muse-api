# Meta Muse API examples (useapi.net): AI video, images and agent chat on muse.ai

Runnable examples for the [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) by [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api): make images and 10-second videos with sound using **Muse (muse.ai)**, Meta's AI agent, through a REST API that runs on your own Muse account. Combine up to 9 photos into one picture, restore and colorize old photos, animate a still with spoken dialogue, and replace a person in a video. Every file Muse makes is an asset id the next job takes as an input, so edits chain with no downloads or re-uploads. The free Muse plan works.

| Example | What it does | Tutorial | Tutorial date |
|---|---|---|---|
| [`images-videos/`](./images-videos) | Three photos become one picture of a rider on a vintage motorcycle in the surf, the picture becomes a 10-second video in which she shouts a line, and a woman from a fourth photo replaces her in that video. Also two images from text, and a hundred-year-old portrait restored, colorized and brought to life. Node.js and Python | [How to Generate AI Videos and Images with the Meta Muse API](https://useapi.net/docs/articles/muse-images-videos?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 12, 2026 |
| [`demo/`](./demo) | **Live chat app**: one self-contained HTML page that chats with the Muse agent through the API, with answers streamed live, files and cards, approvals, several live chats at once, workspace files and the agent's permissions. Open the [live demo](https://useapi.net/demos/muse/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) or open `demo/index.html` locally. Vanilla JS, no build | [Chat Streaming Guide](https://useapi.net/docs/api-muse-v1/chat-streaming-guide?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 12, 2026 |
| [`skills/muse-video/`](./skills/muse-video) | **Agent skill** for Claude Code, Codex and other coding agents: ask for an image or a clip and the agent makes it with Muse (text to image, photo compositing, old-photo restoration, talking photos, person swap in a video) and downloads the `.webp` or `.mp4`, never paying twice for a request. Install: `npx skills add useapi/muse-api --skill muse-video`. Bash, curl, jq | [SKILL.md](./skills/muse-video/SKILL.md) | October 12, 2026 |
| [`n8n/`](./n8n) | **n8n app**: upload an old photo, Muse restores and colorizes it, you pick or redo, then the person in it says your line in a 10-second video with sound. 1 or 2 takes, the real share of the week used on the result page, optional Google Drive save, and a Google Sheet batch mode. Core n8n nodes, no community nodes | [n8n template #20989](https://n8n.io/workflows/20989) | October 15, 2026 |
| [MCP server](#mcp-server) | **Hosted MCP server**: connect Claude Code, Cursor, VS Code or Windsurf to `https://api.useapi.net/v1/muse/mcp` and the assistant gets 27 tools for Muse images, videos, chat, files and permissions. Nothing to install or host | [MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) | October 13, 2026 |

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

useapi.net also runs a hosted [Model Context Protocol](https://modelcontextprotocol.io) server for Muse, so an AI assistant such as Claude Code, Cursor or VS Code Copilot can use Muse on your own Muse account. It has 27 tools: generate images and videos, chat with the Muse agent, answer its permission requests, and manage the account's files. Each tool calls the Muse API, so the same rules, limits and allowance apply. Nothing needs to be installed or hosted.

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

Windsurf setup, a curl test, the full list of 27 tools and how long-running videos and chats are handled: [Muse MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api).

## Common questions

- **Does Muse have an API?** Not for what the Muse agent does. Meta sells its Muse Image model on the Meta Model API at about $0.01 per image, but it has no video API and no API for the Muse agent at muse.ai, where images, 10-second videos with sound, photo edits and person swaps are made. useapi.net drives your own Muse account instead, so every job comes out of that account's Muse allowance.
- **Does the free Muse plan work?** Yes. Muse meters each account weekly, as a percent used. On the free plan a video used 2 to 3 percent of the week and an image 0 to 1 percent in our tests, so one free account makes roughly 30 to 50 videos or several hundred images a week. Paid Muse plans have larger allowances. See [usage limits](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api#usage-limits).
- **What does it cost?** A flat [$15/month](https://useapi.net/docs/subscription?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) to useapi.net, which covers every useapi.net API and adds 3 Muse accounts per subscription. There is no per-image or per-video charge from us.
- **How do I set the aspect ratio, length or resolution?** In the prompt: there are no parameters for them. Write `in exactly 16:9 aspect ratio`. Every video is about 10 seconds at about 720p, with sound, and lines written in quotes are spoken.
- **Can I use my own photos and videos?** Yes. Upload them (up to 50 MB each) and pass the `assetId` as `image_1`..`image_9`; video jobs also take `video_1`..`video_3` and `audio_1`..`audio_3`. All inputs of one job must be on the same Muse account.
- **Where does Muse work?** Only in the US and Canada ([Meta](https://about.fb.com/news/2026/09/introducing-muse-small-business/)), so create the Muse account there. Once it is added, you can call the API from anywhere.
- **Is this Meta's official API?** No. useapi.net is an independent, third-party API that is not affiliated with or endorsed by Meta. It runs on a Muse account you own and add yourself.

## 中文说明

这是 [useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) 的 Muse API 示例代码。通过 REST API 调用 Meta 的 AI 助手 **Muse（muse.ai）**，生成图片和带声音、带对白的 10 秒视频：多张照片合成一张图、老照片修复上色、让照片开口说话、视频换人。每个生成的文件都有一个 assetId，可以直接作为下一个任务的输入，无需下载再上传。

- 使用你自己的 Muse 账号，免费版即可。Muse 按周计算额度：免费版每个视频约占每周额度的 2% 到 3%，每张图片约 0% 到 1%。
- 没有画幅、时长、分辨率参数，全部写在提示词里，例如 `in exactly 16:9 aspect ratio`。视频约 10 秒、约 720p，引号里的台词会被说出来。
- 价格：useapi.net 每月 15 美元（含所有 API），不按图片或视频计费。
- Muse 目前只在美国和加拿大开放（[Meta 官方说明](https://about.fb.com/news/2026/09/introducing-muse-small-business/)），账号需要在这两个国家注册；绑定后可以在任何地方调用 API。
- MCP 服务器：在 Claude Code、Cursor、VS Code 或 Windsurf 中连接托管的 MCP 服务器 `https://api.useapi.net/v1/muse/mcp`（Streamable HTTP，`Authorization: Bearer` 填 useapi.net API token），即可获得 27 个工具：生成图片和视频、与 Muse 对话、处理权限请求、管理文件。说明：[Muse MCP Server](https://useapi.net/docs/api-muse-v1/mcp?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。
- useapi.net 是独立的第三方 API，与 Meta 无关联。

中文教程（多图合成、老照片修复、视频换人，含 curl 示例）：[如何通过 Muse API 用 Meta Muse 生成 AI 图片和带配音的视频](https://useapi.net/docs/articles/muse-api-zh?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。完整文档：[Muse API](https://useapi.net/docs/api-muse-v1?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api)。

## About useapi.net

[useapi.net](https://useapi.net/?utm_source=github.com&utm_medium=referral&utm_campaign=muse-api) is an experimental REST API for AI services. The Muse API drives your own Muse account, so you spend that account's weekly Muse allowance instead of paying per image or per video.

Visit our [Discord Server](https://discord.gg/w28uK3cnmF) or [Telegram Channel](https://t.me/use_api) for any support questions and concerns.

We regularly post guides and tutorials on the [YouTube Channel](https://www.youtube.com/@useapi-net).

## License

The example code in this repository is released under the [MIT License](./LICENSE). It covers the example scripts only, not the useapi.net service or API.
