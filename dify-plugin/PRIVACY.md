# Privacy Policy

This privacy policy covers the "Meta Muse by useapi.net" Dify plugin (`useapi/muse_useapi`).

## What the plugin sends, and where

The plugin contacts one place only: `https://api.useapi.net`, the useapi.net Muse API, for every tool call. Finished files are downloaded from the same API, which streams them from your Muse account. It does not send data to analytics services or to any other third party.

Each request to useapi.net carries:

- your useapi.net API token, in the `Authorization` header, so useapi.net can identify your subscription;
- the optional Muse account email you set in the credentials or in a tool;
- the content of the tool call: prompts, chat messages, asset, job and chat ids, file URLs you give, and any image, video or audio file you attach, which is uploaded to your Muse account.

useapi.net runs the request on the Muse account you connected to it. Your prompts, messages, uploads and the files Muse makes are therefore processed by Muse, Meta's AI agent, in that account, and they show in the muse.ai app like any other Muse chat or file.

## What the plugin stores

The plugin stores nothing. It keeps no logs, no cache and no copy of your data, and holds a request only while the tool runs. Dify stores your API token as an encrypted credential; the plugin does not.

Files the plugin returns to Dify (for example a generated `.mp4`) are stored by your Dify instance like any other tool output file.

## Data handled by the services the plugin calls

- **useapi.net** receives the requests above and keeps job records for 7 days. Uploaded and generated files stay in your Muse account, not at useapi.net. How useapi.net collects, uses and shares data is described in its Terms of Service and Privacy Policy: https://useapi.net/docs/legal
- **Meta** processes your prompts, messages, uploads and generated content in your Muse account, under Meta's Privacy Policy: https://www.facebook.com/privacy/policy/

useapi.net is a third-party service. It is not affiliated with, endorsed by or sponsored by Meta.

## Personal data

The plugin does not collect personal data for its own use. Personal data inside the content you send (for example, a photo you upload or a prompt you write) is sent to useapi.net and Muse as described above, only because you asked a tool to process it. Do not send content you are not allowed to share with these services.

## Contact

Questions about this policy: support@useapi.net
