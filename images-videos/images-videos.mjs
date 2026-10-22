/*

Script version 1.0, October 12, 2026

Script to make images and 10-second videos with sound with Meta's Muse agent using the Muse API by useapi.net

Runs the pipeline of the tutorial https://useapi.net/docs/articles/muse-images-videos
1. Uploads the tutorial's five photos with POST /assets: a motorcycle, a rider, a beach, an old portrait, a second rider.
2. Two images from text with POST /jobs/image: a 9:16 portrait and an exactly-16:9 motorcycle shot.
3. One picture from three photos (image_1 + image_2 + image_3): the rider on the motorcycle in the surf.
4. That picture as a 10-second video with a spoken line, with POST /jobs/video. No download or re-upload in between.
5. The old portrait restored and colorized, then brought to life in a video where she speaks.
6. The rider in the surf video swapped for the woman from the fifth photo (video_1 + image_1).

Every generation runs async: the script submits it with async: true, polls GET /jobs/{jobid} every 10 seconds and
downloads the result with GET /assets/{assetId}. Every step is read from prompts.json. A step's image_N / video_N /
audio_N names an input or an earlier step, and the script passes that file's assetId.

Every finished step is saved to output/muse_state.json, so running the script again continues where it stopped
instead of spending your Muse allowance on the finished steps again. On the free Muse plan the full run used
8 percent of the weekly allowance in our test (3 videos at 2 to 3 percent each, the images 0 percent) and took 7.5 minutes.

Installation Instructions:
==========================

You need Node.js v21 or newer installed to run this script. Download and install Node.js from:

- Windows, macOS, Linux: https://nodejs.org/

After installation, verify by running the following command in a terminal:

   node -v

Running the Script:
===================

Usage: node images-videos.mjs <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]

Replace API_TOKEN with your actual useapi.net API token, see https://useapi.net/docs/start-here/setup-useapi
Replace EMAIL with the Muse account added to the Muse API, see https://useapi.net/docs/start-here/setup-muse
If optional PROMPTS_FILE not provided, prompts.json next to this script will be used.
--steps runs only the named steps of prompts.json, plus the earlier steps they need.

Results are saved to the output folder in the current directory. To redo one step, delete its entry under "steps"
in output/muse_state.json and run again.

Example:
--------

node images-videos.mjs user:1234-abcdefhijklmnopqrstuv my@email.com
node images-videos.mjs user:1234-abcdefhijklmnopqrstuv my@email.com --steps portrait-video

Changelog:
==========

- October 12, 2026: Initial release.

*/

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Readable } from 'node:stream';

// Constants
const API = 'https://api.useapi.net/v1/muse';
const DEFAULT_PROMPTS_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'prompts.json');
const OUTPUT_DIR = 'output';
const STATE_FILE = path.join(OUTPUT_DIR, 'muse_state.json');
const SLEEP_POLL = 10 * 1000; // in milliseconds, how often GET /jobs/{jobid} is read
const SLEEP_RETRY = 30 * 1000; // in milliseconds, before retrying 429 (maxJobs busy) or 503
const SLEEP_RATE_LIMIT = 60 * 1000; // in milliseconds, before resubmitting a job Muse turned down with 429
const MAX_RETRIES = 10; // for a POST answered 429 / 503
const MAX_JOB_RETRIES = 3; // for a job that failed with 503 or 429: nothing was made
const INPUT_KEYS = [
    ...Array.from({ length: 9 }, (_, i) => `image_${i + 1}`),
    ...Array.from({ length: 3 }, (_, i) => `video_${i + 1}`),
    ...Array.from({ length: 3 }, (_, i) => `audio_${i + 1}`)
];
const EXTENSIONS = { 'image/webp': 'webp', 'image/jpeg': 'jpg', 'image/png': 'png', 'video/mp4': 'mp4', 'audio/mpeg': 'mp3' };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const elapsedSec = (start) => Math.round((Date.now() - start) / 1000);

// Ids contain ':' and '@', so they are URL-encoded whenever they go into a URL path.
const enc = encodeURIComponent;

const fail = (message) => {
    console.error(`🛑 ${message}`);
    process.exit(1);
};

// --- saved progress -----------------------------------------------------------
// uploads: input name → assetId   steps: step name → { assetId, mime, file }   jobs: step name → jobid not yet finished
let state = { email: null, uploads: {}, steps: {}, jobs: {} };

const loadState = async () => {
    try {
        state = { ...state, ...JSON.parse(await fs.readFile(STATE_FILE, 'utf8')) };
    } catch {
        // no state file yet: a fresh run
    }
};

const saveState = () => fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2) + '\n');

// --- HTTP ---------------------------------------------------------------------
let apiToken;

// Returns { status, headers, json }. Throws only when no answer arrived at all (network error).
const request = async (method, url, body, contentType = 'application/json') => {
    const response = await fetch(`${API}/${url}`, {
        method,
        headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${apiToken}`,
            ...(body ? { 'Content-Type': contentType } : {})
        },
        body: body ? (contentType == 'application/json' ? JSON.stringify(body) : body) : undefined
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
    403: 'Muse refused to make it (its own words are above). Running it again will not help: change the prompt in prompts.json.',
    404: 'Add the account via https://useapi.net/docs/start-here/setup-muse, or pass the right EMAIL.',
    412: 'The account\'s weekly Muse allowance is used up. GET /accounts/{email} shows resetsAt.',
    502: 'Muse made a file the API could not read. Report the jobid to useapi.net support.',
    504: 'Muse did not finish in time, but it may still have made the file. Check GET /jobs/{jobid}?history=true before running the script again.',
    596: 'The account needs attention (Meta security check or a changed password). See https://useapi.net/docs/start-here/setup-muse'
};
const hint = (code) => HINTS[code] ? `\n   ${HINTS[code]}` : '';

// POST with retries on the answers the docs say to retry: 429 (every maxJobs slot busy) and 503 (nothing was made).
// If no answer arrives at all, it is unclear whether the API accepted a job, so a job is never sent again
// automatically. An upload is free and gives the same assetId every time, so it may be sent again.
const post = async (url, body, what, { contentType, idempotent = false } = {}) => {
    for (let attempt = 1; ; attempt++) {
        let response;
        try {
            response = await request('POST', url, body, contentType);
        } catch (error) {
            if (idempotent && attempt < MAX_RETRIES) {
                console.log(`🔄️ ${what} — no answer (${error.message}), retry ${attempt}/${MAX_RETRIES - 1} in ${SLEEP_RETRY / 1000}s`);
                await sleep(SLEEP_RETRY);
                continue;
            }
            fail(`${what} — no answer from the API (${error.message}). It may have been accepted, so it is not sent again.\n` +
                `   Check GET /jobs before running the script again.`);
        }
        if (response.status >= 200 && response.status < 300) return response.json;

        const error = errorOf(response.status, response.json);
        const retryable = response.status == 429 || response.status == 503 || (idempotent && response.status == 502);
        if (!retryable || attempt >= MAX_RETRIES)
            fail(`${what} — HTTP ${response.status}: ${error.message}${hint(response.status)}`);
        const wait = (Number(response.headers.get('retry-after')) * 1000) || SLEEP_RETRY;
        console.log(`🔄️ ${what} — HTTP ${response.status}, retry ${attempt}/${MAX_RETRIES - 1} in ${Math.round(wait / 1000)}s: ${error.message}`);
        await sleep(wait);
    }
};

// Submit a job with async: true (or pick up the job a stopped run left behind), then poll GET /jobs/{jobid} until it
// completes. A job that failed with 503 (Muse failed to make it this time, nothing was made) or 429 (Muse was
// limiting the account, nothing was made) is sent again. Any other failure stops the script with what to do.
const runJob = async (name, type, body) => {
    const startTime = Date.now();
    for (let attempt = 1; ; attempt++) {
        let jobid = state.jobs[name];
        if (jobid)
            console.log(`   ♻️  ${name} — picking up job ${jobid}`);
        else {
            const job = await post(`jobs/${type}`, { ...body, async: true }, `POST /jobs/${type} (${name})`);
            jobid = job.jobid;
            state.jobs[name] = jobid;
            await saveState();
            console.log(`   ⏳ ${name} — job ${jobid}`);
        }

        let job;
        while (true) {
            await sleep(SLEEP_POLL);
            let response;
            try {
                response = await request('GET', `jobs/${enc(jobid)}`);
            } catch {
                continue; // a passing network hiccup: reading the job is free, read it again
            }
            if (response.status == 429 || response.status >= 500) continue;
            if (response.status != 200)
                fail(`GET /jobs (${name}) — HTTP ${response.status}: ${errorOf(response.status, response.json).message}`);
            job = response.json;
            if (job.status != 'started') break;
            console.log(`   ⌛ ${name} — started (${elapsedSec(startTime)}s)`);
        }

        delete state.jobs[name];
        await saveState();
        await fs.writeFile(path.join(OUTPUT_DIR, `${name}.json`), JSON.stringify(job, null, 2) + '\n');

        if (job.status == 'completed') {
            console.log(`✅ ${name} — completed in ${elapsedSec(startTime)}s` +
                (job.result?.text ? `. Muse: "${job.result.text.replace(/\s+/g, ' ').trim()}"` : ''));
            return job;
        }

        const error = errorOf(0, job);
        const retryable = error.code == 503 || error.code == 429;
        if (!retryable || attempt >= MAX_JOB_RETRIES)
            fail(`${name} — job failed (${error.code}): ${error.message}${hint(error.code)}`.replace('{jobid}', enc(jobid)));
        const wait = error.code == 429 ? SLEEP_RATE_LIMIT : SLEEP_POLL;
        console.log(`🔄️ ${name} — job failed (${error.code}), nothing was made, submitting again in ${Math.round(wait / 1000)}s: ${error.message}`);
        await sleep(wait);
    }
};

const fileExists = (file) => fs.access(file).then(() => true, () => false);

// GET /assets/{assetId} streams the file itself (image/webp or video/mp4) from the account's Muse workspace. It is
// saved under its final name only once it has fully arrived, so a broken download leaves no partial file behind.
const download = async (assetId, file) => {
    if (await fileExists(file)) return;
    for (let attempt = 1; attempt <= 3; attempt++) {
        const temp = `${file}.part`;
        try {
            const response = await fetch(`${API}/assets/${enc(assetId)}`, { headers: { 'Authorization': `Bearer ${apiToken}` } });
            if (response.ok) {
                await fs.writeFile(temp, Readable.fromWeb(response.body));
                await fs.rename(temp, file);
                console.log(`   💾 ${file}`);
                return;
            }
            const message = errorOf(response.status, await response.json().catch(() => ({}))).message;
            if (response.status != 502 && response.status != 503) {
                console.error(`⛔ Unable to download ${file} (HTTP ${response.status}): ${message}`);
                return;
            }
        } catch (error) {
            await fs.rm(temp, { force: true });
            console.error(`⛔ Download of ${file} broke off: ${error.message}`);
        }
        await sleep(SLEEP_POLL);
    }
    console.error(`⛔ Unable to download ${file}. Run the script again to retry the download.`);
};

// GET /accounts/{email} reads the account's plan and weekly usage live from Muse.
const readAccount = async (email) => {
    let response;
    try {
        response = await request('GET', `accounts/${enc(email)}`);
    } catch (error) {
        return { error: error.message };
    }
    return response.status == 200 ? response.json : { error: `HTTP ${response.status}: ${errorOf(response.status, response.json).message}`, status: response.status };
};

// --- prompts.json -------------------------------------------------------------
// Check prompts.json before anything is spent, and work out which steps to run. Returns the steps to run.
const plan = (config, only) => {
    const warnings = [];
    const inputs = config.inputs ?? [];
    const steps = config.steps ?? [];
    const known = new Map(); // name → 'input' | step type
    for (const input of inputs) {
        if (!input.name) warnings.push('an input has no name');
        else if (known.has(input.name)) warnings.push(`the name "${input.name}" is used twice`);
        if (!input.url) warnings.push(`input ${input.name}: url is required`);
        known.set(input.name, 'input');
    }
    for (const step of steps) {
        if (!step.name) warnings.push('a step has no name');
        else if (known.has(step.name)) warnings.push(`the name "${step.name}" is used twice`);
        if (step.type != 'image' && step.type != 'video') warnings.push(`step ${step.name}: type must be image or video`);
        if (!step.prompt) warnings.push(`step ${step.name}: prompt is required`);
        else if (step.prompt.length > 5000) warnings.push(`step ${step.name}: prompt is longer than 5000 characters`);
        for (const key of Object.keys(step)) {
            if (['name', 'type', 'prompt'].includes(key)) continue;
            if (!INPUT_KEYS.includes(key)) warnings.push(`step ${step.name}: parameter ${key} is not supported by this script`);
            else if (step.type == 'image' && !key.startsWith('image_')) warnings.push(`step ${step.name}: an image job takes image_1..image_9 only`);
            else if (!known.has(step[key])) warnings.push(`step ${step.name}: ${key} names "${step[key]}", which is not an input or an earlier step`);
        }
        // A prompt that names image_N / video_N / audio_N needs that parameter (the API answers 400 otherwise).
        for (const named of new Set(step.prompt?.match(/\b(image|video|audio)_\d\b/g) ?? []))
            if (!step[named]) warnings.push(`step ${step.name}: the prompt names ${named}, but the step has no ${named}`);
        known.set(step.name, step.type);
    }
    for (const name of only) if (!steps.some((s) => s.name == name)) warnings.push(`--steps: no step named "${name}"`);

    if (warnings.length) {
        warnings.forEach((warning) => console.warn(`⚠️  ${warning}`));
        fail('Execution stopped due to warnings in the prompts file.');
    }

    if (!only.length) return steps;
    // --steps: the named steps plus every earlier step they take a file from.
    const wanted = new Set(only);
    for (const step of [...steps].reverse())
        if (wanted.has(step.name))
            for (const key of INPUT_KEYS) if (step[key]) wanted.add(step[key]);
    return steps.filter((s) => wanted.has(s.name));
};

// --- the pipeline ---------------------------------------------------------------
const execute = async (email, promptsFile, only) => {
    const config = JSON.parse(await fs.readFile(promptsFile, 'utf8'));
    const steps = plan(config, only);
    const todo = steps.filter((s) => !state.steps[s.name]);
    const videos = todo.filter((s) => s.type == 'video').length;
    const images = todo.length - videos;

    const account = await readAccount(email);
    if (account.error)
        fail(`Account ${email} — ${account.error}. See https://useapi.net/docs/start-here/setup-muse`);
    if (account.health && account.health != 'OK')
        fail(`Account ${email} needs attention: ${account.health}. See https://useapi.net/docs/start-here/setup-muse`);
    const { quota } = account;
    console.log(`👤 ${email}: plan ${quota?.tier ?? '?'}, ${quota?.percentUsed ?? '?'}% of the weekly allowance used, resets ${quota?.resetsAt ?? '?'}`);
    console.log(`   This run makes ${images} image(s) and ${videos} video(s). On the free plan that is about ${images + videos * 3}% at most.`);
    if (quota?.quotaStatus && quota.quotaStatus != 'SUFFICIENT')
        fail(`Muse reports the allowance as ${quota.quotaStatus}. It resets at ${quota.resetsAt}`);
    if (quota?.tier == 'HATCH_FREE' && quota.percentUsed + images + videos * 3 > 100)
        console.warn(`⚠️  The run may not fit in what is left this week. Finished steps are kept: run again after ${quota.resetsAt}.`);

    // Step 1 — upload the inputs the chosen steps use, pinned to EMAIL: all inputs of one job must live on the
    // account that runs it. The assetId is built from the file's content, so uploading again changes nothing.
    const needed = new Set(steps.flatMap((s) => INPUT_KEYS.map((k) => s[k]).filter(Boolean)));
    for (const input of config.inputs ?? []) {
        if (!needed.has(input.name) || state.uploads[input.name]) continue;
        const response = await fetch(input.url);
        if (!response.ok) fail(`Input ${input.name} — could not download ${input.url} (HTTP ${response.status})`);
        const mime = (response.headers.get('content-type') ?? '').split(';')[0].trim();
        const bytes = Buffer.from(await response.arrayBuffer());
        const asset = await post(`assets?email=${enc(email)}`, bytes, `POST /assets (${input.name})`, { contentType: mime, idempotent: true });
        state.uploads[input.name] = asset.assetId;
        await saveState();
        console.log(`📤 ${input.name} — uploaded (${asset.mime}, ${asset.bytes} bytes)`);
    }

    // Steps 2 and on — one job each. image_N / video_N / audio_N name an input or an earlier step, swapped for its assetId:
    // a file Muse made is already in the account's workspace, so it goes into the next job with no download or upload.
    const assetOf = (name) => state.uploads[name] ?? state.steps[name]?.assetId;
    let percentUsed = quota?.percentUsed;
    for (const { name, type, ...fields } of steps) {
        if (!state.steps[name]) {
            console.log(`\n${type == 'video' ? '🎬' : '🖼️ '} ${name} (${type})`);
            const body = { ...fields, email };
            for (const key of INPUT_KEYS) if (body[key]) body[key] = assetOf(body[key]);
            const job = await runJob(name, type, body);
            const asset = job.result.assets.find((a) => a.type == type) ?? job.result.assets[0];
            const file = path.join(OUTPUT_DIR, `${name}.${EXTENSIONS[asset.mime] ?? asset.mime.split('/')[1]}`);
            state.steps[name] = { assetId: asset.assetId, mime: asset.mime, file };
            const after = await readAccount(email);
            if (after.quota?.percentUsed != null) {
                console.log(`   📊 weekly allowance used: ${percentUsed ?? '?'}% → ${after.quota.percentUsed}%`);
                percentUsed = after.quota.percentUsed;
            }
            await saveState();
        }
        await download(state.steps[name].assetId, state.steps[name].file);
    }

    console.log(`\n🎉 Done. Files are in ${path.resolve(OUTPUT_DIR)}`);
    for (const { name } of steps) console.log(`   ${state.steps[name].file}`);
    console.log(`\nEvery file stays in the account's Muse workspace: pass its assetId (in ${STATE_FILE}) as image_N or video_N of your next job.`);
};

const main = async () => {
    const args = process.argv.slice(2);
    const stepsAt = args.indexOf('--steps');
    const only = stepsAt >= 0 ? (args[stepsAt + 1] ?? '').split(',').map((s) => s.trim()).filter(Boolean) : [];
    const [token, email, promptsFile = DEFAULT_PROMPTS_FILE] = args.filter((_, i) => stepsAt < 0 || (i != stepsAt && i != stepsAt + 1));
    apiToken = token;

    if (!apiToken || !email || (stepsAt >= 0 && !only.length)) {
        console.error('Usage: node images-videos.mjs <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]');
        process.exit(1);
    }

    console.info('Script v1.0');
    console.info('Node version is: ' + process.version);

    await fs.mkdir(OUTPUT_DIR, { recursive: true });
    await loadState();
    if (state.email && state.email != email)
        fail(`${STATE_FILE} belongs to ${state.email}. Use that email, or move the output folder away to start fresh.`);
    state.email = email;

    const start = Date.now();
    try {
        console.info('START EXECUTION', new Date(start));
        await execute(email, promptsFile, only);
    } catch (error) {
        console.error('⛔ Error during execution:', error.stack || error);
        process.exitCode = 1;
    } finally {
        console.info('COMPLETED', new Date());
        console.info('EXECUTION ELAPSED', `${elapsedSec(start)} seconds`);
    }
};

main();
