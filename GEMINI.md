# Muse via useapi.net

This extension connects the hosted useapi.net Muse MCP server (`useapi-muse`, 37 tools). The tools make Muse images and videos, chat with the Muse agent and answer its permission requests, use the agent's browser and manage the Library, on your Muse (muse.ai) subscription.

- Endpoint: https://api.useapi.net/v1/muse/mcp (Streamable HTTP), authorized with the user's useapi.net API token in `USEAPI_TOKEN`.
- Before the tools work, the user needs a useapi.net API token (https://useapi.net/docs/start-here/setup-useapi) and a Muse account connected at https://useapi.net/docs/start-here/setup-muse.
- If a tool returns 401, ask the user to check `USEAPI_TOKEN` (`gemini extensions config useapi-muse`). If it says no account is configured, point them to the setup page above.
- Each image or video uses part of the weekly allowance of the user's Muse subscription. Ask before starting many or long jobs, and report job status and links when they finish.
- Full tool list and limits: https://useapi.net/docs/api-muse-v1/mcp

The extension also ships the `muse-video` agent skill from `skills/`, which calls the same API with curl and reads `USEAPI_TOKEN` from the environment.

useapi.net is a paid third-party API service ($15/month covers every useapi.net API and 3 Muse accounts), not affiliated with Meta.
