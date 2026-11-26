# Changelog

## 0.1.0 (2026-11-25)

First release.

- 13 tools for the useapi.net Muse API: Generate image (text to image, up to 9 input images), Generate video (about 10 seconds with sound: text to video, image to video and talking photos, video to video), Get job status, List running jobs, Muse chat, Get Muse chat, Answer a Muse permission request, List Muse chats, Upload a file to Muse, List Muse Library, Download a Muse file, List Muse accounts and Get Muse account usage.
- Several Muse accounts: with the email left empty, useapi.net sends each job to a healthy account with allowance left. A default email in the credentials pins every tool to one account.
- Inputs take an asset id or a Dify file; files are uploaded to the account the other inputs belong to.
- An optional aspect ratio adds "In exactly <ratio> aspect ratio" to the prompt, as Muse follows it best.
- Generations submit the job and wait up to 120 seconds for images and 180 for videos by default (up to 420 in workflows), under Dify's 600-second limit; a job still running returns its `jobid` for Get job status.
- Results come back as readable text, JSON, workflow variables (`jobid`, `status`, `asset_ids`, `reply`, `chat_id`, `approval_ids`) and files.
- Muse's refusals are explained by code: a repeated request (409), a refusal (403), the weekly allowance (412) and the 24-hour video limit (429).
- `answer_approval` answers once (`allow_once`) or denies (`deny`); a lasting "always allow" can only be given by the user in muse.ai.
- Documents are attached as plain text (HTML as `.html.txt`, with a PDF version available through Download a Muse file); only inert image, video, audio, PDF and text types are attached as they are, anything else (SVG, unknown) as an opaque `.bin` file.
- Interface in English, Simplified Chinese, Japanese and Brazilian Portuguese.
