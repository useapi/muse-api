"""

Script version 1.0, October 12, 2026

Script to make images and 10-second videos with sound with Meta's Muse agent using the Muse API v1 by useapi.net 🚀

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

You need Python 3.x installed to run this script (standard library only). Download and install Python from:

- Windows, macOS, Linux: https://www.python.org/

After installation, verify by running the following command in a terminal:

   python3 --version

Running the Script:
===================

Usage: python3 images-videos.py <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]

Replace API_TOKEN with your actual useapi.net API token, see https://useapi.net/docs/start-here/setup-useapi
Replace EMAIL with the Muse account added to the Muse API, see https://useapi.net/docs/start-here/setup-muse
If optional PROMPTS_FILE not provided, prompts.json next to this script will be used.
--steps runs only the named steps of prompts.json, plus the earlier steps they need.

Results are saved to the output folder in the current directory. To redo one step, delete its entry under "steps"
in output/muse_state.json and run again.

Example:
--------

python3 images-videos.py user:1234-abcdefhijklmnopqrstuv my@email.com
python3 images-videos.py user:1234-abcdefhijklmnopqrstuv my@email.com --steps portrait-video

Changelog:
==========

- October 12, 2026: Initial release.

"""

import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime


# Constants
API = 'https://api.useapi.net/v1/muse'
DEFAULT_PROMPTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts.json')
OUTPUT_DIR = 'output'
STATE_FILE = os.path.join(OUTPUT_DIR, 'muse_state.json')
SLEEP_POLL = 10  # in seconds, how often GET /jobs/{jobid} is read
SLEEP_RETRY = 30  # in seconds, before retrying 429 (maxJobs busy) or 503
SLEEP_RATE_LIMIT = 60  # in seconds, before resubmitting a job Muse turned down with 429
MAX_RETRIES = 10  # for a POST answered 429 / 503
MAX_JOB_RETRIES = 3  # for a job that failed with 503 or 429: nothing was made
INPUT_KEYS = [f'image_{i}' for i in range(1, 10)] + [f'video_{i}' for i in range(1, 4)] + [f'audio_{i}' for i in range(1, 4)]
EXTENSIONS = {'image/webp': 'webp', 'image/jpeg': 'jpg', 'image/png': 'png', 'video/mp4': 'mp4', 'audio/mpeg': 'mp3'}

# api.useapi.net's Cloudflare edge rejects urllib's default User-Agent (error 1010), so send a browser-like one.
USER_AGENT = 'Mozilla/5.0 (compatible; images-videos.py)'

api_token = None


def elapsed_sec(start):
    return round(time.time() - start)


# Ids contain ':' and '@', so they are URL-encoded whenever they go into a URL path.
def enc(value):
    return urllib.parse.quote(value, safe='')


def fail(message):
    print(f'🛑 {message}', file=sys.stderr)
    sys.exit(1)


# --- saved progress -----------------------------------------------------------
# uploads: input name → assetId   steps: step name → { assetId, mime, file }   jobs: step name → jobid not yet finished
state = {'email': None, 'uploads': {}, 'steps': {}, 'jobs': {}}


def load_state():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            state.update(json.load(f))
    except (OSError, ValueError):
        pass  # no state file yet: a fresh run


def save_state():
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(state, indent=2, ensure_ascii=False) + '\n')


# --- HTTP ---------------------------------------------------------------------
class NoAnswer(Exception):
    pass


def request(method, url, body=None, content_type='application/json'):
    """Returns (status, headers, json). Raises NoAnswer only when no answer arrived at all (network error)."""
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {api_token}', 'User-Agent': USER_AGENT}
    data = None
    if body is not None:
        headers['Content-Type'] = content_type
        data = json.dumps(body).encode('utf-8') if content_type == 'application/json' else body
    req = urllib.request.Request(f'{API}/{url}', data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            status, response_headers, text = response.status, response.headers, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        status, response_headers, text = e.code, e.headers, e.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError) as e:
        raise NoAnswer(str(getattr(e, 'reason', e)))
    try:
        payload = json.loads(text) if text else {}
    except ValueError:
        payload = {'error': text}
    return status, response_headers, payload


def error_of(status, payload):
    """An error answer is { error: "…", code } or a failed job record { …, error: { code, message } }."""
    error = payload.get('error') if isinstance(payload, dict) else None
    if isinstance(error, str):
        return status, error
    if isinstance(error, dict):
        return error.get('code', status), error.get('message', json.dumps(payload))
    return status, json.dumps(payload)


# What to do about an error that stops the script.
HINTS = {
    401: 'Check the API token.',
    403: 'Muse refused to make it (its own words are above). Running it again will not help: change the prompt in prompts.json.',
    404: 'Add the account via https://useapi.net/docs/start-here/setup-muse, or pass the right EMAIL.',
    412: "The account's weekly Muse allowance is used up. GET /accounts/{email} shows resetsAt.",
    502: 'Muse made a file the API could not read. Report the jobid to useapi.net support.',
    504: 'Muse did not finish in time, but it may still have made the file. Check GET /jobs/{jobid}?history=true before running the script again.',
    596: 'The account needs attention (Meta security check or a changed password). See https://useapi.net/docs/start-here/setup-muse',
}


def hint(code):
    return f'\n   {HINTS[code]}' if code in HINTS else ''


def post(url, body, what, content_type='application/json', idempotent=False):
    """POST with retries on the answers the docs say to retry: 429 (every maxJobs slot busy) and 503 (nothing was made).
    If no answer arrives at all, it is unclear whether the API accepted a job, so a job is never sent again
    automatically. An upload is free and gives the same assetId every time, so it may be sent again."""
    attempt = 0
    while True:
        attempt += 1
        try:
            status, headers, payload = request('POST', url, body, content_type)
        except NoAnswer as e:
            if idempotent and attempt < MAX_RETRIES:
                print(f'🔄️ {what} — no answer ({e}), retry {attempt}/{MAX_RETRIES - 1} in {SLEEP_RETRY}s')
                time.sleep(SLEEP_RETRY)
                continue
            fail(f'{what} — no answer from the API ({e}). It may have been accepted, so it is not sent again.\n'
                 f'   Check GET /jobs before running the script again.')
        if 200 <= status < 300:
            return payload
        _, message = error_of(status, payload)
        retryable = status in (429, 503) or (idempotent and status == 502)
        if not retryable or attempt >= MAX_RETRIES:
            fail(f'{what} — HTTP {status}: {message}{hint(status)}')
        try:
            wait = int(headers.get('Retry-After') or SLEEP_RETRY)
        except ValueError:
            wait = SLEEP_RETRY
        print(f'🔄️ {what} — HTTP {status}, retry {attempt}/{MAX_RETRIES - 1} in {wait}s: {message}')
        time.sleep(wait)


def run_job(name, job_type, body):
    """Submit a job with async: true (or pick up the job a stopped run left behind), then poll GET /jobs/{jobid} until
    it completes. A job that failed with 503 (Muse failed to make it this time, nothing was made) or 429 (Muse was
    limiting the account, nothing was made) is sent again. Any other failure stops the script with what to do."""
    start = time.time()
    attempt = 0
    while True:
        attempt += 1
        jobid = state['jobs'].get(name)
        if jobid:
            print(f'   ♻️  {name} — picking up job {jobid}')
        else:
            job = post(f'jobs/{job_type}', {**body, 'async': True}, f'POST /jobs/{job_type} ({name})')
            jobid = job['jobid']
            state['jobs'][name] = jobid
            save_state()
            print(f'   ⏳ {name} — job {jobid}')

        while True:
            time.sleep(SLEEP_POLL)
            try:
                status, _, job = request('GET', f'jobs/{enc(jobid)}')
            except NoAnswer:
                continue  # a passing network hiccup: reading the job is free, read it again
            if status == 429 or status >= 500:
                continue
            if status != 200:
                fail(f'GET /jobs ({name}) — HTTP {status}: {error_of(status, job)[1]}')
            if job.get('status') != 'started':
                break
            print(f'   ⌛ {name} — started ({elapsed_sec(start)}s)')

        del state['jobs'][name]
        save_state()
        with open(os.path.join(OUTPUT_DIR, f'{name}.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps(job, indent=2, ensure_ascii=False) + '\n')

        if job.get('status') == 'completed':
            text = ' '.join((job.get('result', {}).get('text') or '').split())
            print(f'✅ {name} — completed in {elapsed_sec(start)}s' + (f'. Muse: "{text}"' if text else ''))
            return job

        code, message = error_of(0, job)
        if code not in (503, 429) or attempt >= MAX_JOB_RETRIES:
            fail(f'{name} — job failed ({code}): {message}{hint(code)}'.replace('{jobid}', enc(jobid)))
        wait = SLEEP_RATE_LIMIT if code == 429 else SLEEP_POLL
        print(f'🔄️ {name} — job failed ({code}), nothing was made, submitting again in {wait}s: {message}')
        time.sleep(wait)


def download(asset_id, file):
    """GET /assets/{assetId} streams the file itself (image/webp or video/mp4) from the account's Muse workspace. It is
    saved under its final name only once it has fully arrived, so a broken download leaves no partial file behind."""
    if os.path.exists(file):
        return
    for _ in range(3):
        temp = f'{file}.part'
        req = urllib.request.Request(f'{API}/assets/{enc(asset_id)}',
                                     headers={'Authorization': f'Bearer {api_token}', 'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=300) as response, open(temp, 'wb') as f:
                shutil.copyfileobj(response, f)
            os.replace(temp, file)
            print(f'   💾 {file}')
            return
        except urllib.error.HTTPError as e:
            message = error_of(e.code, _json_or_empty(e.read()))[1]
            if e.code not in (502, 503):
                print(f'⛔ Unable to download {file} (HTTP {e.code}): {message}', file=sys.stderr)
                return
        except (urllib.error.URLError, OSError) as e:
            print(f'⛔ Download of {file} broke off: {e}', file=sys.stderr)
        if os.path.exists(temp):
            os.remove(temp)
        time.sleep(SLEEP_POLL)
    print(f'⛔ Unable to download {file}. Run the script again to retry the download.', file=sys.stderr)


def _json_or_empty(raw):
    try:
        return json.loads(raw.decode('utf-8'))
    except ValueError:
        return {}


def read_account(email):
    """GET /accounts/{email} reads the account's plan and weekly usage live from Muse."""
    try:
        status, _, payload = request('GET', f'accounts/{enc(email)}')
    except NoAnswer as e:
        return {'error': str(e)}
    if status == 200:
        return payload
    return {'error': f'HTTP {status}: {error_of(status, payload)[1]}'}


def fetch_input(url):
    """Downloads one input photo and returns (bytes, MIME type from the server)."""
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.read(), (response.headers.get('Content-Type') or '').split(';')[0].strip()
    except (urllib.error.URLError, OSError) as e:
        fail(f'Could not download {url} ({e})')


# --- prompts.json -------------------------------------------------------------
def plan(config, only):
    """Check prompts.json before anything is spent, and work out which steps to run. Returns the steps to run."""
    warnings = []
    inputs = config.get('inputs', [])
    steps = config.get('steps', [])
    known = {}  # name → 'input' | step type
    for item in inputs:
        name = item.get('name')
        if not name:
            warnings.append('an input has no name')
        elif name in known:
            warnings.append(f'the name "{name}" is used twice')
        if not item.get('url'):
            warnings.append(f'input {name}: url is required')
        known[name] = 'input'
    for step in steps:
        name, job_type, prompt = step.get('name'), step.get('type'), step.get('prompt')
        if not name:
            warnings.append('a step has no name')
        elif name in known:
            warnings.append(f'the name "{name}" is used twice')
        if job_type not in ('image', 'video'):
            warnings.append(f'step {name}: type must be image or video')
        if not prompt:
            warnings.append(f'step {name}: prompt is required')
        elif len(prompt) > 5000:
            warnings.append(f'step {name}: prompt is longer than 5000 characters')
        for key, value in step.items():
            if key in ('name', 'type', 'prompt'):
                continue
            if key not in INPUT_KEYS:
                warnings.append(f'step {name}: parameter {key} is not supported by this script')
            elif job_type == 'image' and not key.startswith('image_'):
                warnings.append(f'step {name}: an image job takes image_1..image_9 only')
            elif value not in known:
                warnings.append(f'step {name}: {key} names "{value}", which is not an input or an earlier step')
        # A prompt that names image_N / video_N / audio_N needs that parameter (the API answers 400 otherwise).
        for named in sorted(set(re.findall(r'\b(?:image|video|audio)_\d\b', prompt or ''))):
            if not step.get(named):
                warnings.append(f'step {name}: the prompt names {named}, but the step has no {named}')
        known[name] = job_type
    for name in only:
        if not any(s.get('name') == name for s in steps):
            warnings.append(f'--steps: no step named "{name}"')

    if warnings:
        for warning in warnings:
            print(f'⚠️  {warning}', file=sys.stderr)
        fail('Execution stopped due to warnings in the prompts file.')

    if not only:
        return steps
    # --steps: the named steps plus every earlier step they take a file from.
    wanted = set(only)
    for step in reversed(steps):
        if step['name'] in wanted:
            wanted.update(step[k] for k in INPUT_KEYS if step.get(k))
    return [s for s in steps if s['name'] in wanted]


# --- the pipeline ---------------------------------------------------------------
def execute(email, prompts_file, only):
    with open(prompts_file, encoding='utf-8') as f:
        config = json.load(f)
    steps = plan(config, only)
    todo = [s for s in steps if s['name'] not in state['steps']]
    videos = sum(1 for s in todo if s['type'] == 'video')
    images = len(todo) - videos

    account = read_account(email)
    if account.get('error'):
        fail(f"Account {email} — {account['error']}. See https://useapi.net/docs/start-here/setup-muse")
    if account.get('health') and account['health'] != 'OK':
        fail(f"Account {email} needs attention: {account['health']}. See https://useapi.net/docs/start-here/setup-muse")
    quota = account.get('quota') or {}
    print(f"👤 {email}: plan {quota.get('tier', '?')}, {quota.get('percentUsed', '?')}% of the weekly allowance used, "
          f"resets {quota.get('resetsAt', '?')}")
    print(f'   This run makes {images} image(s) and {videos} video(s). On the free plan that is about {images + videos * 3}% at most.')
    if quota.get('quotaStatus') and quota['quotaStatus'] != 'SUFFICIENT':
        fail(f"Muse reports the allowance as {quota['quotaStatus']}. It resets at {quota.get('resetsAt')}")
    if quota.get('tier') == 'HATCH_FREE' and (quota.get('percentUsed') or 0) + images + videos * 3 > 100:
        print(f"⚠️  The run may not fit in what is left this week. Finished steps are kept: run again after {quota.get('resetsAt')}.",
              file=sys.stderr)

    # Step 1 — upload the inputs the chosen steps use, pinned to EMAIL: all inputs of one job must live on the
    # account that runs it. The assetId is built from the file's content, so uploading again changes nothing.
    needed = {s[k] for s in steps for k in INPUT_KEYS if s.get(k)}
    for item in config.get('inputs', []):
        name = item['name']
        if name not in needed or name in state['uploads']:
            continue
        data, mime = fetch_input(item['url'])
        asset = post(f'assets?email={enc(email)}', data, f'POST /assets ({name})', content_type=mime, idempotent=True)
        state['uploads'][name] = asset['assetId']
        save_state()
        print(f"📤 {name} — uploaded ({asset.get('mime')}, {asset.get('bytes')} bytes)")

    # Steps 2+ — one job each. image_N / video_N / audio_N name an input or an earlier step, swapped for its assetId:
    # a file Muse made is already in the account's workspace, so it goes into the next job with no download or upload.
    def asset_of(name):
        return state['uploads'].get(name) or state['steps'][name]['assetId']

    percent_used = quota.get('percentUsed')
    for step in steps:
        name, job_type = step['name'], step['type']
        if name not in state['steps']:
            print(f"\n{'🎬' if job_type == 'video' else '🖼️ '} {name} ({job_type})")
            body = {k: v for k, v in step.items() if k not in ('name', 'type')}
            body['email'] = email
            for key in INPUT_KEYS:
                if body.get(key):
                    body[key] = asset_of(body[key])
            job = run_job(name, job_type, body)
            assets = job['result']['assets']
            asset = next((a for a in assets if a.get('type') == job_type), assets[0])
            mime = asset['mime']
            file = os.path.join(OUTPUT_DIR, f"{name}.{EXTENSIONS.get(mime, mime.split('/')[-1])}")
            state['steps'][name] = {'assetId': asset['assetId'], 'mime': mime, 'file': file}
            after = (read_account(email).get('quota') or {}).get('percentUsed')
            if after is not None:
                print(f"   📊 weekly allowance used: {'?' if percent_used is None else percent_used}% → {after}%")
                percent_used = after
            save_state()
        download(state['steps'][name]['assetId'], state['steps'][name]['file'])

    print(f'\n🎉 Done. Files are in {os.path.abspath(OUTPUT_DIR)}')
    for step in steps:
        print(f"   {state['steps'][step['name']]['file']}")
    print(f"\nEvery file stays in the account's Muse workspace: pass its assetId (in {STATE_FILE}) as image_N or video_N of your next job.")


def main():
    global api_token
    args = sys.argv[1:]
    only = []
    if '--steps' in args:
        at = args.index('--steps')
        only = [s.strip() for s in (args[at + 1] if at + 1 < len(args) else '').split(',') if s.strip()]
        args = args[:at] + args[at + 2:]
        if not only:
            args = []
    if len(args) < 2:
        print('Usage: python3 images-videos.py <API_TOKEN> <EMAIL> [PROMPTS_FILE] [--steps name,name]', file=sys.stderr)
        sys.exit(1)
    api_token, email = args[0], args[1]
    prompts_file = args[2] if len(args) > 2 else DEFAULT_PROMPTS_FILE

    print('Script v1.0')
    print('Python version is: ' + sys.version.split()[0])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    load_state()
    if state['email'] and state['email'] != email:
        fail(f"{STATE_FILE} belongs to {state['email']}. Use that email, or move the output folder away to start fresh.")
    state['email'] = email

    start = time.time()
    try:
        print('START EXECUTION', datetime.now())
        execute(email, prompts_file, only)
    except KeyboardInterrupt:
        print('\n⛔ Stopped. Run the script again to continue where it stopped.', file=sys.stderr)
        sys.exit(130)
    finally:
        print('COMPLETED', datetime.now())
        print('EXECUTION ELAPSED', f'{elapsed_sec(start)} seconds')


if __name__ == '__main__':
    main()
