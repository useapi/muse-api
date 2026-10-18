"""

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

You need Python 3.8 or newer. It uses the standard library only, so there is nothing to install.

- Windows, macOS, Linux: https://www.python.org/downloads/

After installation, verify by running the following command in a terminal:

   python3 --version

Running the Script:
===================

Usage: python3 narrated-short.py <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"]
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

python3 narrated-short.py user:1234-abcdefhijklmnopqrstuv my@email.com "how a single volcano cooled the whole planet in 1816"
python3 narrated-short.py user:1234-abcdefhijklmnopqrstuv my@email.com "the history of the paperclip" --scenes 2

Changelog:
==========

- October 18, 2026: Initial release.

"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Constants
API = 'https://api.useapi.net/v1/muse'
DEFAULT_PROMPTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts.json')
DEFAULT_TTS_VOICE = 'Aria (avocado_v2:MAI_01)'
OUTPUT_DIR = 'output'
SLEEP_POLL_JOB = 10  # in seconds, how often GET /jobs/{jobid} is read
SLEEP_POLL_CHAT = 8  # in seconds, how often GET /chats/{chatId} is read
SLEEP_RETRY = 30  # in seconds, before retrying a POST answered 429 or 503
SLEEP_RATE_LIMIT = 60  # in seconds, before resubmitting a job Muse turned down with 429
MAX_RETRIES = 10  # for a POST answered 429 / 503
MAX_JOB_RETRIES = 3  # for a job that failed with 503 or 429: nothing was made
MAX_CHAT_SECONDS = 10 * 60  # a chat that has not finished after 10 minutes stops the script
# api.useapi.net's Cloudflare edge rejects urllib's default User-Agent (error 1010, HTTP 403), so send a browser-like one.
USER_AGENT = 'Mozilla/5.0 (compatible; narrated-short.py)'

USAGE = ('Usage: python3 narrated-short.py <API_TOKEN> <EMAIL> "<TOPIC>" [--scenes 1-3] [--narrator "<description>"] '
         '[--fixed-voice] [--tts-voice "<voice>"] [--prompts <file>]')


def elapsed_sec(start):
    return round(time.time() - start)


def enc(value):
    # Ids contain ':' and '@', so they are URL-encoded whenever they go into a URL path.
    return urllib.parse.quote(value, safe='')


class Stop(Exception):
    pass


def fail(message):
    raise Stop(message)


def fill(template, values):
    # Fill {name} placeholders of a prompts.json template. JSON braces such as {"title": string} are left as they are.
    return re.sub(r'\{(\w+)\}', lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), template)


def slugify(text):
    # The topic as a file name: lowercase words joined by '-', whole words up to about 60 characters.
    slug = ''
    for word in [w for w in re.split(r'[^a-z0-9]+', text.lower()) if w]:
        if slug and len(slug) + 1 + len(word) > 60:
            break
        slug = f'{slug}-{word}' if slug else word[:60]
    return slug or 'short'


# --- saved progress -----------------------------------------------------------
state = {}
state_file = None
state_lock = threading.Lock()


def save_state():
    with state_lock:
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(state, indent=2) + '\n')


def write_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def log(message):
    print(message, flush=True)


# --- HTTP ---------------------------------------------------------------------
api_token = None


class Answer:
    def __init__(self, status, headers, data):
        self.status = status
        self.headers = headers
        self.json = data


def request(method, url, body=None):
    # Returns an Answer. Raises only when no answer arrived at all (network error).
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {api_token}', 'User-Agent': USER_AGENT}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(f'{API}/{url}', data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            status, response_headers, text = response.status, response.headers, response.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as error:
        status, response_headers, text = error.code, error.headers, error.read().decode('utf-8', 'replace')
    try:
        parsed = json.loads(text) if text else {}
    except ValueError:
        parsed = {'error': text}
    return Answer(status, response_headers, parsed)


def error_of(status, data):
    # An error answer is { error: "…", code } or a failed job record { …, error: { code, message } }.
    error = data.get('error') if isinstance(data, dict) else None
    if isinstance(error, dict):
        return error.get('code', status), error.get('message') or json.dumps(data)
    if isinstance(error, str):
        return status, error
    return status, json.dumps(data)


# What to do about an error that stops the script.
HINTS = {
    401: 'Check the API token.',
    403: 'Muse refused to make it (its own words are above). Running it again will not help: change the topic or prompts.json.',
    404: 'Add the account via https://useapi.net/docs/start-here/setup-muse, or pass the right EMAIL.',
    412: "The account's weekly Muse allowance is used up. GET /accounts/{email} shows resetsAt.",
    502: 'Muse made a file the API could not read, or did not take the message. Check GET /jobs/{jobid}?history=true before running again.',
    504: 'Muse did not finish in time, or the connection dropped, but it may still have made the file or got the message. Check GET /jobs/{jobid}?history=true or GET /chats before running the script again.',
    596: 'The account needs attention (Meta security check or a changed password). See https://useapi.net/docs/start-here/setup-muse',
}


def hint(code):
    return f'\n   {HINTS[code]}' if code in HINTS else ''


def post(url, body, what):
    # POST with retries on the two answers the docs say nothing was sent or made: 429 (Muse is limiting the account, or
    # every maxJobs slot is busy) and 503. If no answer arrives at all, it is unclear whether the API took the request,
    # so it is never sent again automatically.
    attempt = 0
    while True:
        attempt += 1
        try:
            answer = request('POST', url, body)
        except Exception as error:
            fail(f'{what}: no answer from the API ({error}). It may have been accepted, so it is not sent again.\n'
                 '   Check GET /jobs and GET /chats before running the script again.')
        if 200 <= answer.status < 300:
            return answer.json
        _, message = error_of(answer.status, answer.json)
        retryable = answer.status in (429, 503)
        if not retryable or attempt >= MAX_RETRIES:
            fail(f'{what}: HTTP {answer.status}: {message}{hint(answer.status)}')
        try:
            wait = int(answer.headers.get('retry-after') or 0) or SLEEP_RETRY
        except ValueError:
            wait = SLEEP_RETRY
        log(f'   {what}: HTTP {answer.status}, retry {attempt}/{MAX_RETRIES - 1} in {wait}s: {message}')
        time.sleep(wait)


def read(url, what):
    # A GET that is free to repeat: a network error, 429 or 5xx is read again.
    for _ in range(MAX_RETRIES):
        try:
            answer = request('GET', url)
        except Exception:
            answer = None
        if answer is not None and answer.status == 200:
            return answer.json
        if answer is not None and answer.status != 429 and answer.status < 500:
            fail(f'{what}: HTTP {answer.status}: {error_of(answer.status, answer.json)[1]}')
        time.sleep(SLEEP_POLL_JOB)
    fail(f'{what}: no usable answer after {MAX_RETRIES} tries')


# --- chats --------------------------------------------------------------------
def run_chat(name, message, files=None):
    # Send a message with POST /chats and read GET /chats/{chatId} until Muse is done. A chat runs no job, so a chat
    # is never sent twice: when a run stops mid-chat, the next run reads the same chatId from the state file.
    # Muse can ask permission before an action. The workflow needs none (the prompts say "No public links"), so a
    # request to upload, publish or share is denied, and anything else (running ffmpeg, saving a file) is allowed once.
    start = time.time()
    if not state['chats'].get(name):
        body = {'message': message, 'email': state['email']}
        if files:
            body['files'] = files
        answer = post('chats', body, f'POST /chats ({name})')
        state['chats'][name] = answer['chatId']
        save_state()
        log(f"   {name}: chat {answer['chatId']}")
    else:
        log(f"   {name}: picking up chat {state['chats'][name]}")

    chat_id = state['chats'][name]
    answered = set()
    while True:
        time.sleep(SLEEP_POLL_CHAT)
        chat = read(f'chats/{enc(chat_id)}', f'GET /chats ({name})')
        pending = chat.get('pendingApprovals') or []
        for approval in pending:
            if approval['approvalId'] in answered:
                continue
            answered.add(approval['approvalId'])
            text = json.dumps(approval).lower()
            deny = any(word in text for word in ('upload', 'public', 'share', 'remote storage', 'remote_storage'))
            decision = 'deny' if deny else 'allow_once'
            log(f"   {name}: Muse asks \"{approval.get('title') or approval.get('question') or 'permission'}\", answering {decision}")
            post(f"chats/{enc(chat_id)}/approvals/{enc(approval['approvalId'])}", {'decision': decision},
                 f'POST /chats/approvals ({name})')
        messages = chat.get('messages') or []
        done = (chat.get('status') in ('completed', 'interrupted', 'failed') and not pending
                and messages and messages[-1].get('role') == 'assistant')
        if done:
            write_json(os.path.join(state['dir'], f'{name}.chat.json'), chat)
            log(f"   {name}: {chat.get('status')} in {elapsed_sec(start)}s")
            return chat
        if time.time() - start > MAX_CHAT_SECONDS:
            fail(f'{name}: the chat has not finished after {MAX_CHAT_SECONDS // 60} minutes. Read it with GET /chats/{enc(chat_id)}')


def ask_again(name):
    # A chat is never sent twice on its own. To ask again, its chatId has to go from state.json.
    return f'\n   To ask again, delete "{name}" under "chats" in {state_file} and run the script again.'


def assistant_text(chat):
    texts = [m['text'] for m in chat.get('messages', []) if m.get('role') == 'assistant' and m.get('text')]
    return texts[-1] if texts else ''


def assistant_files(chat, kind):
    return [f for m in chat.get('messages', []) if m.get('role') == 'assistant'
            for f in m.get('files') or [] if isinstance(f, dict) and f.get('type') == kind]


# --- jobs ---------------------------------------------------------------------
def run_job(name, body):
    # Submit a video job with async: true (or pick up the job a stopped run left behind), then poll GET /jobs/{jobid}
    # until it completes. A job that failed with 503 (Muse failed to make it this time, nothing was made) or 429 (Muse
    # was limiting the account, nothing was made) is sent again. Any other failure stops the script: it may have been
    # charged.
    start = time.time()
    attempt = 0
    while True:
        attempt += 1
        jobid = state['jobs'].get(name)
        if jobid:
            log(f'   {name}: picking up job {jobid}')
        else:
            job = post('jobs/video', {**body, 'email': state['email'], 'async': True}, f'POST /jobs/video ({name})')
            jobid = job['jobid']
            state['jobs'][name] = jobid
            save_state()
            log(f'   {name}: job {jobid}')

        while True:
            time.sleep(SLEEP_POLL_JOB)
            job = read(f'jobs/{enc(jobid)}', f'GET /jobs ({name})')
            if job.get('status') != 'started':
                break
            log(f'   {name}: started ({elapsed_sec(start)}s)')
        write_json(os.path.join(state['dir'], f'{name}.job.json'), job)

        if job.get('status') == 'completed':
            text = re.sub(r'\s+', ' ', (job.get('result') or {}).get('text') or '').strip()
            log(f'   {name}: completed in {elapsed_sec(start)}s' + (f'. Muse: "{text}"' if text else ''))
            return job

        code, message = error_of(0, job)
        if code not in (503, 429) or attempt >= MAX_JOB_RETRIES:
            fail(f'{name}: job failed ({code}): {message}{hint(code)}'.replace('{jobid}', enc(jobid)) +
                 f'\n   It is not sent again automatically. To send it anyway, delete "{name}" under "jobs" in {state_file}')
        del state['jobs'][name]
        save_state()
        wait = SLEEP_RATE_LIMIT if code == 429 else SLEEP_POLL_JOB
        log(f'   {name}: job failed ({code}), nothing was made, submitting again in {wait}s: {message}')
        time.sleep(wait)


def all_scenes(task, count):
    # Run every scene at once and wait for all of them, so a scene that stops the script does not cut the others
    # short: their jobs finish and are saved for the next run. The first problem is then reported.
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(task, i) for i in range(count)]
        errors = [f.exception() for f in futures]
    for error in errors:
        if error:
            raise error


def download(asset_id, file):
    # GET /assets/{assetId} streams the file itself from the account's Muse workspace. It is saved under its final
    # name only once it has fully arrived, so a broken download leaves no partial file behind.
    temp = f'{file}.part'
    for _ in range(3):
        req = urllib.request.Request(f'{API}/assets/{enc(asset_id)}', headers={'Authorization': f'Bearer {api_token}', 'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=300) as response, open(temp, 'wb') as f:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(temp, file)
            return
        except urllib.error.HTTPError as error:
            try:
                message = error_of(error.code, json.loads(error.read() or b'{}'))[1]
            except ValueError:
                message = str(error)
            if error.code not in (429, 503):
                fail(f'Unable to download {file} (HTTP {error.code}): {message}')
        except Exception as error:
            log(f'   Download of {file} broke off: {error}')
        if os.path.exists(temp):
            os.remove(temp)
        time.sleep(SLEEP_POLL_JOB)
    fail(f'Unable to download {file}. Run the script again to retry the download: the Short is already made.')


def read_account(email):
    # GET /accounts/{email} reads the account's plan and weekly usage live from Muse.
    try:
        answer = request('GET', f'accounts/{enc(email)}')
    except Exception as error:
        return {'error': str(error)}
    if answer.status == 200:
        return answer.json
    return {'error': f'HTTP {answer.status}: {error_of(answer.status, answer.json)[1]}'}


# --- the script, as JSON ------------------------------------------------------
def parse_script(text, scenes):
    # Muse answered the JSON prompt with clean JSON in our tests, but a reply wrapped in ``` fences or in a sentence
    # still parses: the fences are dropped and the outermost { … } is read.
    unfenced = re.sub(r'```(?:json)?', '', text, flags=re.IGNORECASE).strip()
    start, end = unfenced.find('{'), unfenced.rfind('}')
    if start < 0 or end <= start:
        return None
    try:
        script = json.loads(unfenced[start:end + 1])
    except ValueError:
        return None
    items = script.get('scenes') if isinstance(script, dict) else None
    ok = (isinstance(items, list) and len(items) == scenes and
          all(isinstance(s, dict) and isinstance(s.get('line'), str) and s['line'].strip() and
              isinstance(s.get('visual'), str) and s['visual'].strip() for s in items))
    return script if ok else None


def write_script(prompts, topic, scenes):
    shape = ', '.join(['{"line": string, "visual": string}'] * scenes)
    message = fill(prompts['script'], {'seconds': scenes * 10, 'topic': topic, 'scenes': scenes, 'shape': shape})
    for attempt in (1, 2):
        name = 'script' if attempt == 1 else 'script-retry'
        chat = run_chat(name, message)
        script = parse_script(assistant_text(chat), scenes)
        if script:
            return script
        log(f"   {name}: the reply is not a script of {scenes} scenes{', asking once more' if attempt == 1 else ''}")
    fail(f"Muse did not return a usable JSON script twice. Its replies are in the *.chat.json files of {state['dir']}. To try again, move that folder away.")


# --- the workflow -------------------------------------------------------------
def execute(opts):
    with open(opts['prompts_file'], encoding='utf-8') as f:
        prompts = json.load(f)
    for key in ['narrator', 'script', 'scene', 'join'] + (['tts', 'sceneWithVoice'] if opts['fixed_voice'] else []):
        if not isinstance(prompts.get(key), str) or not prompts[key]:
            fail(f'{opts["prompts_file"]}: "{key}" is missing')
    narrator = opts['narrator'] if opts['narrator'] is not None else prompts['narrator']

    email = opts['email']
    account = read_account(email)
    if account.get('error'):
        fail(f"Account {email}: {account['error']}. See https://useapi.net/docs/start-here/setup-muse")
    if account.get('health') and account['health'] != 'OK':
        fail(f"Account {email} needs attention: {account['health']}. See https://useapi.net/docs/start-here/setup-muse")
    quota = account.get('quota') or {}
    log(f"{email}: plan {quota.get('tier', '?')}, {quota.get('percentUsed', '?')}% of the weekly allowance used, resets {quota.get('resetsAt', '?')}")
    log(f"This Short makes {opts['scenes']} video(s). On the free plan a video uses 2 to 3% of the week, the chats about 0%.")
    if quota.get('quotaStatus') and quota['quotaStatus'] != 'SUFFICIENT':
        fail(f"Muse reports the allowance as {quota['quotaStatus']}. It resets at {quota.get('resetsAt')}")

    # 1. The script, as JSON.
    if not state['script']:
        log('\n1. Script')
        state['script'] = write_script(prompts, opts['topic'], opts['scenes'])
        save_state()
    scenes = state['script']['scenes']
    log(f"\n\"{state['script'].get('title') or opts['topic']}\"")
    for i, scene in enumerate(scenes):
        log(f"   {i + 1}. {scene['line']}")

    # 1b. With --fixed-voice: one text to speech chat per line, all at once.
    if opts['fixed_voice']:
        log('\n1b. Voice')

        def voice(i):
            name = f'voice-{i + 1}'
            if state['voices'].get(name):
                return
            file = f"{state['slug']}-line-{i + 1}.mp3"
            chat = run_chat(name, fill(prompts['tts'], {'voice': opts['tts_voice'], 'line': scenes[i]['line'], 'file': file}))
            audio = assistant_files(chat, 'audio')
            if not audio:
                fail(f'{name}: Muse attached no audio file. It said: "{assistant_text(chat)}"{ask_again(name)}')
            state['voices'][name] = audio[-1]['assetId']
            save_state()

        all_scenes(voice, len(scenes))

    # 2 and 3. One video job per scene, all at once, each polled until it completes.
    log('\n2. Scenes')

    def scene_job(i):
        name = f'scene-{i + 1}'
        if state['clips'].get(name):
            return
        scene = scenes[i]
        if opts['fixed_voice']:
            body = {'prompt': fill(prompts['sceneWithVoice'], {'visual': scene['visual']}),
                    'audio_1': state['voices'][f'voice-{i + 1}']}
        else:
            body = {'prompt': fill(prompts['scene'], {'visual': scene['visual'], 'narrator': narrator, 'line': scene['line']})}
        job = run_job(name, body)
        videos = [a for a in (job.get('result') or {}).get('assets', []) if a.get('type') == 'video']
        # With audio_1, Muse lays the voice onto its clip with ffmpeg: that copy has origin "made". Muse's raw clip
        # (origin "generated") carries a voice Muse made up instead, so it is never used for --fixed-voice.
        if opts['fixed_voice']:
            clip = next((a for a in videos if a.get('origin') == 'made'), None)
        else:
            clip = videos[0] if videos else None
        if not clip:
            wanted = 'video with origin "made"' if opts['fixed_voice'] else 'video'
            fail(f"{name}: the job lists no {wanted}. The job record is in {os.path.join(state['dir'], name + '.job.json')}")
        # The job id stays in state.json until a clip is taken from it, so a run that stops here never sends the job again.
        state['jobs'].pop(name, None)
        state['clips'][name] = clip['assetId']
        save_state()

    all_scenes(scene_job, len(scenes))
    clips = [state['clips'][f'scene-{i + 1}'] for i in range(len(scenes))]

    # 4. One chat joins the clips with ffmpeg in the account's workspace.
    if not state['short']:
        if len(clips) == 1:
            state['short'] = clips[0]
        else:
            log('\n3. Join')
            names = [f'video_{i + 1}' for i in range(len(clips))]
            videos = ' and '.join(names) if len(names) == 2 else ', '.join(names)
            chat = run_chat('join', fill(prompts['join'], {'videos': videos, 'file': f"{state['slug']}.mp4"}), clips)
            short = assistant_files(chat, 'video')
            if not short:
                fail(f'join: Muse attached no video. It said: "{assistant_text(chat)}"{ask_again("join")}')
            state['short'] = short[-1]['assetId']
        save_state()

    # 5. Download the Short.
    file = os.path.join(OUTPUT_DIR, f"{state['slug']}.mp4")
    download(state['short'], file)
    after = read_account(email)
    log(f'\nDone: {os.path.abspath(file)}')
    if (after.get('quota') or {}).get('percentUsed') is not None:
        log(f"Weekly allowance used: {quota.get('percentUsed', '?')}% before this run, {after['quota']['percentUsed']}% now (Muse reports whole percents).")
    log(f"The clips and the Short stay in the account's Muse workspace. Their asset ids are in {state_file}")


def parse_args(args):
    opts = {'scenes': 3, 'narrator': None, 'fixed_voice': False, 'tts_voice': DEFAULT_TTS_VOICE,
            'prompts_file': DEFAULT_PROMPTS_FILE}
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ('--scenes', '--narrator', '--tts-voice', '--prompts'):
            if i + 1 >= len(args):
                raise ValueError(f'{arg} needs a value')
            i += 1
            value = args[i]
            if arg == '--scenes':
                if not re.fullmatch(r'[0-9]+', value):
                    raise ValueError('--scenes must be 1, 2 or 3')
                opts['scenes'] = int(value)
            elif arg == '--narrator':
                opts['narrator'] = value
            elif arg == '--tts-voice':
                opts['tts_voice'] = value
            else:
                opts['prompts_file'] = value
        elif arg == '--fixed-voice':
            opts['fixed_voice'] = True
        elif arg.startswith('--'):
            raise ValueError(f'unknown option {arg}')
        else:
            positional.append(arg)
        i += 1
    if len(positional) != 3 or not positional[0] or not positional[1] or not positional[2].strip():
        raise ValueError('API_TOKEN, EMAIL and TOPIC are required')
    if opts['scenes'] not in (1, 2, 3):
        raise ValueError('--scenes must be 1, 2 or 3')
    if opts['narrator'] is not None and not opts['narrator'].strip():
        raise ValueError('--narrator is empty')
    opts['token'], opts['email'], opts['topic'] = positional[0], positional[1], positional[2].strip()
    return opts


def main():
    global api_token, state, state_file
    try:
        opts = parse_args(sys.argv[1:])
    except ValueError as error:
        print(f'{error}\n{USAGE}', file=sys.stderr)
        sys.exit(1)
    api_token = opts['token']

    print('Script v1.0')
    print('Python version is: ' + sys.version.split()[0])

    slug = slugify(opts['topic'])
    folder = os.path.join(OUTPUT_DIR, slug)
    os.makedirs(folder, exist_ok=True)
    state_file = os.path.join(folder, 'state.json')
    state = {'topic': opts['topic'], 'email': opts['email'], 'slug': slug, 'dir': folder, 'scenes': opts['scenes'],
             'fixedVoice': opts['fixed_voice'], 'script': None, 'chats': {}, 'jobs': {}, 'voices': {}, 'clips': {},
             'short': None}
    if os.path.exists(state_file):
        with open(state_file, encoding='utf-8') as f:
            saved = json.load(f)
        if (saved.get('topic') != opts['topic'] or saved.get('email') != opts['email']
                or saved.get('scenes') != opts['scenes'] or saved.get('fixedVoice') != opts['fixed_voice']):
            print(f"{state_file} is a run of \"{saved.get('topic')}\" with {saved.get('email')}, {saved.get('scenes')} scene(s)"
                  f"{', --fixed-voice' if saved.get('fixedVoice') else ''}. Run with the same options to continue it, "
                  f'or move {folder} away to start fresh.', file=sys.stderr)
            sys.exit(1)
        state.update(saved)
        print(f'Continuing the run saved in {state_file}')

    start = time.time()
    try:
        print('START EXECUTION', datetime.now())
        execute(opts)
    except Stop as error:
        print(f'\nStopped: {error}', file=sys.stderr)
        exit_code = 1
    except Exception as error:
        print(f'\nError during execution: {error!r}', file=sys.stderr)
        exit_code = 1
    else:
        exit_code = 0
    finally:
        print('COMPLETED', datetime.now())
        print('EXECUTION ELAPSED', f'{elapsed_sec(start)} seconds')
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
