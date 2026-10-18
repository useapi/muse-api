/*

Script version 1.0, October 18, 2026

Script to make a 30-second narrated vertical Short from a topic with Meta's Muse agent, using the Muse API v1 by useapi.net

Runs the workflow of the tutorial section
https://useapi.net/docs/articles/muse-images-videos#make-a-30-second-narrated-short-script-three-scenes-one-join
1. One chat (POST /chats) writes the script as JSON: a title, and per scene the narrator's line and the shot.
2. One 10-second 9:16 video job per scene (POST /jobs/video, async), all at once. Every prompt carries the same
   narrator description and the scene's line in quotes, so Muse speaks it word for word in the same kind of voice.
3. The jobs are polled with GET /jobs/{jobid} until each one completes.
4. One more chat joins the clips with ffmpeg in Muse's workspace and attaches the result.
5. The Short is downloaded with GET /assets/{assetId} to output/<topic>.mp4.

With --fixed-voice, each line is first spoken by Muse's text to speech (one chat per line), and each video job takes
that MP3 as audio_1. The job then lists Muse's ffmpeg-made copy with origin "made", which is the one used.

Every prompt is read from prompts.json. Progress is saved to output/<topic>/state.json, so running the script again
with the same topic continues where it stopped instead of spending your Muse allowance again.

Installation Instructions:
==========================

You need Node.js v21 or newer installed to run this script. Download and install Node.js from:

- Windows, macOS, Linux: https://nodejs.org/

After installation, verify by running the following command in a terminal:

   node -v

Running the Script:
===================

Usage: node narrated-short.mjs <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"]
                               [--fixed-voice] [--tts-voice "<voice>"] [--prompts <file>]

Replace API_TOKEN with your actual useapi.net API token, see https://useapi.net/docs/start-here/setup-useapi
Replace EMAIL with the Muse account added to the Muse API, see https://useapi.net/docs/start-here/setup-muse
TOPIC is what the Short is about.
--scenes is the number of 10-second scenes, 1 to 3 (default 3). A chat takes up to 3 videos, so 3 is the most one
  join can take.
--narrator replaces the narrator description of prompts.json.
--fixed-voice speaks the lines with Muse's text to speech and lays them onto the clips (one voice for certain).
--tts-voice is the text to speech voice for --fixed-voice (default "Aria (avocado_v2:MAI_01)").
--prompts is another prompts file (default prompts.json next to this script).

Example:
--------

node narrated-short.mjs user:1234-abcdefhijklmnopqrstuv my@email.com "how a single volcano cooled the whole planet in 1816"
node narrated-short.mjs user:1234-abcdefhijklmnopqrstuv my@email.com "the history of the paperclip" --scenes 2

Changelog:
==========

- October 18, 2026: Initial release.

*/

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Readable } from 'node:stream';

// Constants
const API = 'https://api.useapi.net/v1/muse';
const DEFAULT_PROMPTS_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'prompts.json');
const DEFAULT_TTS_VOICE = 'Aria (avocado_v2:MAI_01)';
const OUTPUT_DIR = 'output';
const SLEEP_POLL_JOB = 10 * 1000; // in milliseconds, how often GET /jobs/{jobid} is read
const SLEEP_POLL_CHAT = 8 * 1000; // in milliseconds, how often GET /chats/{chatId} is read
const SLEEP_RETRY = 30 * 1000; // in milliseconds, before retrying a POST answered 429 or 503
const SLEEP_RATE_LIMIT = 60 * 1000; // in milliseconds, before resubmitting a job Muse turned down with 429
const MAX_RETRIES = 10; // for a POST answered 429 / 503
const MAX_JOB_RETRIES = 3; // for a job that failed with 503 or 429: nothing was made
const MAX_CHAT_MS = 10 * 60 * 1000; // a chat that has not finished after 10 minutes stops the script

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const elapsedSec = (start) => Math.round((Date.now() - start) / 1000);

// Ids contain ':' and '@', so they are URL-encoded whenever they go into a URL path.
const enc = encodeURIComponent;

class Stop extends Error {}
const fail = (message) => { throw new Stop(message); };

// Fill {name} placeholders of a prompts.json template. JSON braces such as {"title": string} are left as they are.
const fill = (template, values) => template.replace(/\{(\w+)\}/g, (all, key) => key in values ? String(values[key]) : all);

// The topic as a file name: lowercase words joined by '-', whole words up to about 60 characters.
const slugify = (text) => {
    const words = text.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
    let slug = '';
    for (const word of words) {
        if (slug && slug.length + 1 + word.length > 60) break;
        slug = slug ? `${slug}-${word}` : word.slice(0, 60);
    }
    return slug || 'short';
};

// --- saved progress -----------------------------------------------------------
let stateFile;
let state;

const saveState = () => fs.writeFile(stateFile, JSON.stringify(state, null, 2) + '\n');

// --- HTTP ---------------------------------------------------------------------
let apiToken;

// Returns { status, headers, json }. Throws only when no answer arrived at all (network error).
const request = async (method, url, body) => {
    const response = await fetch(`${API}/${url}`, {
        method,
        headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${apiToken}`,
            ...(body ? { 'Content-Type': 'application/json' } : {})
        },
        body: body ? JSON.stringify(body) : undefined
    });
    const text = await response.text();
    let json;
    try { json = text ? JSON.parse(text) : {}; } catch { json = { error: text }; }
    return { status: response.status, headers: response.headers, json };
};

// An error answer is { error: "…", code } or a failed job record { …, error: { code, message } }.
const errorOf = (status, json) => ({
    code: json?.error?.code ?? status,
    message: typeof json?.error === 'string' ? json.error : json?.error?.message ?? JSON.stringify(json)
});

// What to do about an error that stops the script.
const HINTS = {
    401: 'Check the API token.',
    403: 'Muse refused to make it (its own words are above). Running it again will not help: change the topic or prompts.json.',
    404: 'Add the account via https://useapi.net/docs/start-here/setup-muse, or pass the right EMAIL.',
    412: 'The account\'s weekly Muse allowance is used up. GET /accounts/{email} shows resetsAt.',
    502: 'Muse made a file the API could not read, or did not take the message. Check GET /jobs/{jobid}?history=true before running again.',
    504: 'Muse did not finish in time, or the connection dropped, but it may still have made the file or got the message. Check GET /jobs/{jobid}?history=true or GET /chats before running the script again.',
    596: 'The account needs attention (Meta security check or a changed password). See https://useapi.net/docs/start-here/setup-muse'
};
const hint = (code) => HINTS[code] ? `\n   ${HINTS[code]}` : '';

// POST with retries on the two answers the docs say nothing was sent or made: 429 (Muse is limiting the account, or
// every maxJobs slot is busy) and 503. If no answer arrives at all, it is unclear whether the API took the request,
// so it is never sent again automatically.
const post = async (url, body, what) => {
    for (let attempt = 1; ; attempt++) {
        let response;
        try {
            response = await request('POST', url, body);
        } catch (error) {
            fail(`${what}: no answer from the API (${error.message}). It may have been accepted, so it is not sent again.\n` +
                '   Check GET /jobs and GET /chats before running the script again.');
        }
        if (response.status >= 200 && response.status < 300) return response.json;

        const error = errorOf(response.status, response.json);
        const retryable = response.status == 429 || response.status == 503;
        if (!retryable || attempt >= MAX_RETRIES)
            fail(`${what}: HTTP ${response.status}: ${error.message}${hint(response.status)}`);
        const wait = (Number(response.headers.get('retry-after')) * 1000) || SLEEP_RETRY;
        console.log(`   ${what}: HTTP ${response.status}, retry ${attempt}/${MAX_RETRIES - 1} in ${Math.round(wait / 1000)}s: ${error.message}`);
        await sleep(wait);
    }
};

// A GET that is free to repeat: a network error, 429 or 5xx is read again.
const read = async (url, what) => {
    for (let attempt = 1; ; attempt++) {
        let response;
        try {
            response = await request('GET', url);
        } catch {
            response = null;
        }
        if (response?.status == 200) return response.json;
        if (response && response.status != 429 && response.status < 500)
            fail(`${what}: HTTP ${response.status}: ${errorOf(response.status, response.json).message}`);
        if (attempt >= MAX_RETRIES) fail(`${what}: no usable answer after ${MAX_RETRIES} tries`);
        await sleep(SLEEP_POLL_JOB);
    }
};

// --- chats --------------------------------------------------------------------
// Send a message with POST /chats and read GET /chats/{chatId} until Muse is done. A chat runs no job, so a chat is
// never sent twice: when a run stops mid-chat, the next run reads the same chatId from the state file.
// Muse can ask permission before an action. The workflow needs none (the prompts say "No public links"), so a request
// to upload, publish or share is denied, and anything else (running ffmpeg, saving a file) is allowed once.
const runChat = async (name, message, files) => {
    const startTime = Date.now();
    if (!state.chats[name]) {
        const body = { message, email: state.email, ...(files?.length ? { files } : {}) };
        const answer = await post('chats', body, `POST /chats (${name})`);
        state.chats[name] = answer.chatId;
        await saveState();
        console.log(`   ${name}: chat ${answer.chatId}`);
    } else
        console.log(`   ${name}: picking up chat ${state.chats[name]}`);

    const chatId = state.chats[name];
    const answered = new Set();
    while (true) {
        await sleep(SLEEP_POLL_CHAT);
        const chat = await read(`chats/${enc(chatId)}`, `GET /chats (${name})`);
        for (const approval of chat.pendingApprovals ?? []) {
            if (answered.has(approval.approvalId)) continue;
            answered.add(approval.approvalId);
            const text = JSON.stringify(approval).toLowerCase();
            const deny = ['upload', 'public', 'share', 'remote storage', 'remote_storage'].some((word) => text.includes(word));
            const decision = deny ? 'deny' : 'allow_once';
            console.log(`   ${name}: Muse asks "${approval.title ?? approval.question ?? 'permission'}", answering ${decision}`);
            await post(`chats/${enc(chatId)}/approvals/${enc(approval.approvalId)}`, { decision }, `POST /chats/approvals (${name})`);
        }
        const last = chat.messages?.at(-1);
        const done = ['completed', 'interrupted', 'failed'].includes(chat.status) && !(chat.pendingApprovals ?? []).length && last?.role == 'assistant';
        if (done) {
            await fs.writeFile(path.join(state.dir, `${name}.chat.json`), JSON.stringify(chat, null, 2) + '\n');
            console.log(`   ${name}: ${chat.status} in ${elapsedSec(startTime)}s`);
            return chat;
        }
        if (Date.now() - startTime > MAX_CHAT_MS)
            fail(`${name}: the chat has not finished after ${MAX_CHAT_MS / 60000} minutes. Read it with GET /chats/${enc(chatId)}`);
    }
};

// Run every scene at once and wait for all of them, so a scene that stops the script does not cut the others short:
// their jobs finish and are saved for the next run. The first problem is then reported.
const allScenes = async (tasks) => {
    const results = await Promise.allSettled(tasks);
    const failed = results.find((r) => r.status == 'rejected');
    if (failed) throw failed.reason;
};

// A chat is never sent twice on its own. To ask again, its chatId has to go from state.json.
const askAgain = (name) => `\n   To ask again, delete "${name}" under "chats" in ${stateFile} and run the script again.`;

const assistantText = (chat) => chat.messages.filter((m) => m.role == 'assistant' && m.text).map((m) => m.text).at(-1) ?? '';
const assistantFiles = (chat, type) => chat.messages.filter((m) => m.role == 'assistant')
    .flatMap((m) => m.files ?? []).filter((f) => typeof f == 'object' && f.type == type);

// --- jobs ---------------------------------------------------------------------
// Submit a video job with async: true (or pick up the job a stopped run left behind), then poll GET /jobs/{jobid}
// until it completes. A job that failed with 503 (Muse failed to make it this time, nothing was made) or 429 (Muse was
// limiting the account, nothing was made) is sent again. Any other failure stops the script: it may have been charged.
const runJob = async (name, body) => {
    const startTime = Date.now();
    for (let attempt = 1; ; attempt++) {
        let jobid = state.jobs[name];
        if (jobid)
            console.log(`   ${name}: picking up job ${jobid}`);
        else {
            const job = await post('jobs/video', { ...body, email: state.email, async: true }, `POST /jobs/video (${name})`);
            jobid = job.jobid;
            state.jobs[name] = jobid;
            await saveState();
            console.log(`   ${name}: job ${jobid}`);
        }

        let job;
        while (true) {
            await sleep(SLEEP_POLL_JOB);
            job = await read(`jobs/${enc(jobid)}`, `GET /jobs (${name})`);
            if (job.status != 'started') break;
            console.log(`   ${name}: started (${elapsedSec(startTime)}s)`);
        }
        await fs.writeFile(path.join(state.dir, `${name}.job.json`), JSON.stringify(job, null, 2) + '\n');

        if (job.status == 'completed') {
            console.log(`   ${name}: completed in ${elapsedSec(startTime)}s` +
                (job.result?.text ? `. Muse: "${job.result.text.replace(/\s+/g, ' ').trim()}"` : ''));
            return job;
        }

        const error = errorOf(0, job);
        const retryable = error.code == 503 || error.code == 429;
        if (!retryable || attempt >= MAX_JOB_RETRIES)
            fail(`${name}: job failed (${error.code}): ${error.message}${hint(error.code)}`.replace('{jobid}', enc(jobid)) +
                `\n   It is not sent again automatically. To send it anyway, delete "${name}" under "jobs" in ${stateFile}`);
        delete state.jobs[name];
        await saveState();
        const wait = error.code == 429 ? SLEEP_RATE_LIMIT : SLEEP_POLL_JOB;
        console.log(`   ${name}: job failed (${error.code}), nothing was made, submitting again in ${Math.round(wait / 1000)}s: ${error.message}`);
        await sleep(wait);
    }
};

// GET /assets/{assetId} streams the file itself from the account's Muse workspace. It is saved under its final name
// only once it has fully arrived, so a broken download leaves no partial file behind.
const download = async (assetId, file) => {
    for (let attempt = 1; attempt <= 3; attempt++) {
        const temp = `${file}.part`;
        try {
            const response = await fetch(`${API}/assets/${enc(assetId)}`, { headers: { 'Authorization': `Bearer ${apiToken}` } });
            if (response.ok) {
                await fs.writeFile(temp, Readable.fromWeb(response.body));
                await fs.rename(temp, file);
                return;
            }
            const message = errorOf(response.status, await response.json().catch(() => ({}))).message;
            if (response.status != 429 && response.status != 503) fail(`Unable to download ${file} (HTTP ${response.status}): ${message}`);
        } catch (error) {
            if (error instanceof Stop) throw error;
            await fs.rm(temp, { force: true });
            console.error(`   Download of ${file} broke off: ${error.message}`);
        }
        await sleep(SLEEP_POLL_JOB);
    }
    fail(`Unable to download ${file}. Run the script again to retry the download: the Short is already made.`);
};

// GET /accounts/{email} reads the account's plan and weekly usage live from Muse.
const readAccount = async (email) => {
    try {
        const response = await request('GET', `accounts/${enc(email)}`);
        return response.status == 200 ? response.json : { error: `HTTP ${response.status}: ${errorOf(response.status, response.json).message}` };
    } catch (error) {
        return { error: error.message };
    }
};

// --- the script, as JSON ------------------------------------------------------
// Muse answered the JSON prompt with clean JSON in our tests, but a reply wrapped in ``` fences or in a sentence still
// parses: the fences are dropped and the outermost { … } is read.
const parseScript = (text, scenes) => {
    const unfenced = text.replace(/```(?:json)?/gi, '').trim();
    const start = unfenced.indexOf('{');
    const end = unfenced.lastIndexOf('}');
    if (start < 0 || end <= start) return null;
    let script;
    try { script = JSON.parse(unfenced.slice(start, end + 1)); } catch { return null; }
    const ok = Array.isArray(script?.scenes) && script.scenes.length == scenes &&
        script.scenes.every((s) => typeof s?.line == 'string' && s.line.trim() && typeof s?.visual == 'string' && s.visual.trim());
    return ok ? script : null;
};

const writeScript = async (prompts, topic, scenes) => {
    const shape = Array(scenes).fill('{"line": string, "visual": string}').join(', ');
    const message = fill(prompts.script, { seconds: scenes * 10, topic, scenes, shape });
    for (let attempt = 1; attempt <= 2; attempt++) {
        const name = attempt == 1 ? 'script' : 'script-retry';
        const chat = await runChat(name, message);
        const script = parseScript(assistantText(chat), scenes);
        if (script) return script;
        console.log(`   ${name}: the reply is not a script of ${scenes} scenes${attempt == 1 ? ', asking once more' : ''}`);
    }
    fail(`Muse did not return a usable JSON script twice. Its replies are in the *.chat.json files of ${state.dir}. To try again, move that folder away.`);
};

// --- the workflow -------------------------------------------------------------
const execute = async (opts) => {
    const prompts = JSON.parse(await fs.readFile(opts.promptsFile, 'utf8'));
    for (const key of ['narrator', 'script', 'scene', 'join', ...(opts.fixedVoice ? ['tts', 'sceneWithVoice'] : [])])
        if (typeof prompts[key] != 'string' || !prompts[key]) fail(`${opts.promptsFile}: "${key}" is missing`);
    const narrator = opts.narrator ?? prompts.narrator;

    const account = await readAccount(opts.email);
    if (account.error) fail(`Account ${opts.email}: ${account.error}. See https://useapi.net/docs/start-here/setup-muse`);
    if (account.health && account.health != 'OK')
        fail(`Account ${opts.email} needs attention: ${account.health}. See https://useapi.net/docs/start-here/setup-muse`);
    const { quota } = account;
    console.log(`${opts.email}: plan ${quota?.tier ?? '?'}, ${quota?.percentUsed ?? '?'}% of the weekly allowance used, resets ${quota?.resetsAt ?? '?'}`);
    console.log(`This Short makes ${opts.scenes} video(s). On the free plan a video uses 2 to 3% of the week, the chats about 0%.`);
    if (quota?.quotaStatus && quota.quotaStatus != 'SUFFICIENT')
        fail(`Muse reports the allowance as ${quota.quotaStatus}. It resets at ${quota.resetsAt}`);

    // 1. The script, as JSON.
    if (!state.script) {
        console.log('\n1. Script');
        state.script = await writeScript(prompts, opts.topic, opts.scenes);
        await saveState();
    }
    const { scenes } = state.script;
    console.log(`\n"${state.script.title ?? opts.topic}"`);
    scenes.forEach((s, i) => console.log(`   ${i + 1}. ${s.line}`));

    // 1b. With --fixed-voice: one text to speech chat per line, all at once.
    if (opts.fixedVoice) {
        console.log('\n1b. Voice');
        await allScenes(scenes.map(async (scene, i) => {
            const name = `voice-${i + 1}`;
            if (state.voices[name]) return;
            const file = `${state.slug}-line-${i + 1}.mp3`;
            const chat = await runChat(name, fill(prompts.tts, { voice: opts.ttsVoice, line: scene.line, file }));
            const audio = assistantFiles(chat, 'audio').at(-1);
            if (!audio) fail(`${name}: Muse attached no audio file. It said: "${assistantText(chat)}"${askAgain(name)}`);
            state.voices[name] = audio.assetId;
            await saveState();
        }));
    }

    // 2 and 3. One video job per scene, all at once, each polled until it completes.
    console.log('\n2. Scenes');
    await allScenes(scenes.map(async (scene, i) => {
        const name = `scene-${i + 1}`;
        if (state.clips[name]) return;
        const body = opts.fixedVoice
            ? { prompt: fill(prompts.sceneWithVoice, { visual: scene.visual }), audio_1: state.voices[`voice-${i + 1}`] }
            : { prompt: fill(prompts.scene, { visual: scene.visual, narrator, line: scene.line }) };
        const job = await runJob(name, body);
        const videos = (job.result?.assets ?? []).filter((a) => a.type == 'video');
        // With audio_1, Muse lays the voice onto its clip with ffmpeg: that copy has origin "made". Muse's raw clip
        // (origin "generated") carries a voice Muse made up instead, so it is never used for --fixed-voice.
        const clip = opts.fixedVoice ? videos.find((a) => a.origin == 'made') : videos[0];
        if (!clip)
            fail(`${name}: the job lists no ${opts.fixedVoice ? 'video with origin "made"' : 'video'}. The job record is in ${path.join(state.dir, `${name}.job.json`)}`);
        // The job id stays in state.json until a clip is taken from it, so a run that stops here never sends the job again.
        delete state.jobs[name];
        state.clips[name] = clip.assetId;
        await saveState();
    }));
    const clips = scenes.map((_, i) => state.clips[`scene-${i + 1}`]);

    // 4. One chat joins the clips with ffmpeg in the account's workspace.
    if (!state.short) {
        if (clips.length == 1)
            state.short = clips[0];
        else {
            console.log('\n3. Join');
            const names = clips.map((_, i) => `video_${i + 1}`);
            const videos = names.length == 2 ? names.join(' and ') : names.join(', ');
            const chat = await runChat('join', fill(prompts.join, { videos, file: `${state.slug}.mp4` }), clips);
            const short = assistantFiles(chat, 'video').at(-1);
            if (!short) fail(`join: Muse attached no video. It said: "${assistantText(chat)}"${askAgain('join')}`);
            state.short = short.assetId;
        }
        await saveState();
    }

    // 5. Download the Short.
    const file = path.join(OUTPUT_DIR, `${state.slug}.mp4`);
    await download(state.short, file);
    const after = await readAccount(opts.email);
    console.log(`\nDone: ${path.resolve(file)}`);
    if (after.quota?.percentUsed != null)
        console.log(`Weekly allowance used: ${quota?.percentUsed ?? '?'}% before this run, ${after.quota.percentUsed}% now (Muse reports whole percents).`);
    console.log(`The clips and the Short stay in the account's Muse workspace. Their asset ids are in ${stateFile}`);
};

const USAGE = 'Usage: node narrated-short.mjs <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"] [--fixed-voice] [--tts-voice "<voice>"] [--prompts <file>]';

const parseArgs = (args) => {
    const opts = { scenes: 3, fixedVoice: false, ttsVoice: DEFAULT_TTS_VOICE, promptsFile: DEFAULT_PROMPTS_FILE };
    const positional = [];
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        const value = () => {
            if (i + 1 >= args.length) throw new Error(`${arg} needs a value`);
            return args[++i];
        };
        if (arg == '--scenes') opts.scenes = Number(value());
        else if (arg == '--narrator') opts.narrator = value();
        else if (arg == '--tts-voice') opts.ttsVoice = value();
        else if (arg == '--prompts') opts.promptsFile = value();
        else if (arg == '--fixed-voice') opts.fixedVoice = true;
        else if (arg.startsWith('--')) throw new Error(`unknown option ${arg}`);
        else positional.push(arg);
    }
    [opts.token, opts.email, opts.topic] = positional;
    if (positional.length != 3 || !opts.token || !opts.email || !opts.topic?.trim()) throw new Error('API_TOKEN, EMAIL and TOPIC are required');
    if (!Number.isInteger(opts.scenes) || opts.scenes < 1 || opts.scenes > 3) throw new Error('--scenes must be 1, 2 or 3');
    if (opts.narrator !== undefined && !opts.narrator.trim()) throw new Error('--narrator is empty');
    opts.topic = opts.topic.trim();
    return opts;
};

const main = async () => {
    let opts;
    try {
        opts = parseArgs(process.argv.slice(2));
    } catch (error) {
        console.error(`${error.message}\n${USAGE}`);
        process.exit(1);
    }
    apiToken = opts.token;

    console.info('Script v1.0');
    console.info('Node version is: ' + process.version);

    const slug = slugify(opts.topic);
    const dir = path.join(OUTPUT_DIR, slug);
    await fs.mkdir(dir, { recursive: true });
    stateFile = path.join(dir, 'state.json');
    state = { topic: opts.topic, email: opts.email, slug, dir, scenes: opts.scenes, fixedVoice: opts.fixedVoice, script: null, chats: {}, jobs: {}, voices: {}, clips: {}, short: null };
    try {
        const saved = JSON.parse(await fs.readFile(stateFile, 'utf8'));
        if (saved.topic != opts.topic || saved.email != opts.email || saved.scenes != opts.scenes || saved.fixedVoice != opts.fixedVoice) {
            console.error(`${stateFile} is a run of "${saved.topic}" with ${saved.email}, ${saved.scenes} scene(s)${saved.fixedVoice ? ', --fixed-voice' : ''}. ` +
                `Run with the same options to continue it, or move ${dir} away to start fresh.`);
            process.exit(1);
        }
        state = { ...state, ...saved };
        console.info(`Continuing the run saved in ${stateFile}`);
    } catch {
        // no state file yet: a fresh run
    }

    const start = Date.now();
    try {
        console.info('START EXECUTION', new Date(start));
        await execute(opts);
    } catch (error) {
        if (error instanceof Stop) console.error(`\nStopped: ${error.message}`);
        else console.error('\nError during execution:', error.stack || error);
        process.exitCode = 1;
    } finally {
        console.info('COMPLETED', new Date());
        console.info('EXECUTION ELAPSED', `${elapsedSec(start)} seconds`);
    }
};

main();
