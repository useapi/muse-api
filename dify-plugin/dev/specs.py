"""Single source of truth for every tool: names, parameters, enums and the
four Dify UI languages (en_US, zh_Hans, ja_JP, pt_BR). `dev/gen_tools.py`
writes tools/*.yaml, tools/*.py and the provider's tool list from this file.

Parameter names and limits follow the published API catalog
(https://api.useapi.net/v1/muse/models) and the public API reference
(https://useapi.net/docs/api-muse-v1). Muse has no model, aspect ratio,
resolution or duration parameters: the aspect ratio option here only adds
"In exactly <ratio> aspect ratio" to the prompt, as the docs advise.
LLM-facing descriptions stay in English.
"""

from __future__ import annotations

from typing import Any


def L(en: str, zh: str, ja: str, pt: str) -> dict[str, str]:
    return {"en_US": en, "zh_Hans": zh, "ja_JP": ja, "pt_BR": pt}


def opt(value: str, label: dict[str, str]) -> dict[str, Any]:
    return {"value": value, "label": label}


def same(value: str) -> dict[str, Any]:
    return opt(value, L(value, value, value, value))


def param(
    name: str,
    ptype: str,
    label: dict[str, str],
    human: dict[str, str],
    llm: str | None = None,
    *,
    required: bool = False,
    form: str = "llm",
    default: Any = None,
    options: list[dict[str, Any]] | None = None,
    min: int | None = None,
    max: int | None = None,
) -> dict[str, Any]:
    p: dict[str, Any] = {
        "name": name,
        "type": ptype,
        "required": required,
        "label": label,
        "human_description": human,
    }
    if form == "llm":
        p["llm_description"] = llm or human["en_US"]
    p["form"] = form
    if default is not None:
        p["default"] = default
    if options:
        p["options"] = options
    if min is not None:
        p["min"] = min
    if max is not None:
        p["max"] = max
    return p


def select(
    name: str,
    label: dict[str, str],
    human: dict[str, str],
    options: list[dict[str, Any]],
    llm: str | None = None,
    default: str | None = None,
    form: str = "llm",
) -> dict[str, Any]:
    values = ", ".join(o["value"] for o in options)
    return param(
        name,
        "select",
        label,
        human,
        llm or f"{human['en_US']} One of: {values}.",
        options=options,
        default=default,
        form=form,
    )


# ------------------------------------------------------------------ shared parameters

EMAIL_LABEL = L("Muse account email", "Muse 账号邮箱", "Muse アカウントのメール", "E-mail da conta do Muse")


def EMAIL() -> dict[str, Any]:
    """For requests that useapi.net can route: empty means a healthy account with allowance left."""
    return param(
        "email",
        "string",
        EMAIL_LABEL,
        L(
            "Optional. Leave empty and useapi.net picks a healthy account with allowance left (or the account that holds the inputs). Default: the email in the credentials.",
            "可选。留空时 useapi.net 会选择一个健康且有剩余额度的账号（或存放输入文件的账号）。默认：凭据中的邮箱。",
            "任意。空欄にすると useapi.net が、使用枠が残っている正常なアカウント（または入力ファイルのあるアカウント）を選びます。既定は認証情報のメール。",
            "Opcional. Deixe vazio e a useapi.net escolhe uma conta saudável com cota restante (ou a conta que guarda as entradas). Padrão: o e-mail das credenciais.",
        ),
        "Optional Muse account email. Leave empty: useapi.net picks a healthy account with allowance left. Input asset ids already pin the request to their own account.",
    )


def EMAIL_READ(what_en: str) -> dict[str, Any]:
    """For reads of one account's data."""
    return param(
        "email",
        "string",
        EMAIL_LABEL,
        L(
            "The Muse account to read. Optional when only one account is connected or a default email is set.",
            "要读取的 Muse 账号。只连接了一个账号或已设置默认邮箱时可省略。",
            "読み取る Muse アカウント。接続が 1 つだけ、または既定のメールを設定済みなら省略できます。",
            "A conta do Muse a ler. Opcional quando só uma conta está conectada ou há um e-mail padrão.",
        ),
        f"Email of the Muse account whose {what_en} to read. Optional when only one account is connected or a default email is set.",
    )


JOBID = param(
    "jobid",
    "string",
    L("Job ID", "任务 ID", "ジョブ ID", "ID do job"),
    L(
        "The jobid returned by Generate image or Generate video.",
        "“生成图片”或“生成视频”返回的任务 ID（jobid）。",
        "「画像を生成」または「動画を生成」で返された jobid。",
        "O jobid retornado por Gerar imagem ou Gerar vídeo.",
    ),
    "The jobid from Generate image or Generate video, e.g. j1012...v-u12345-email:john@gmail.com-task:...-bot:muse.",
    required=True,
)

WAIT = param(
    "wait",
    "boolean",
    L("Wait for the result", "等待结果", "結果を待つ", "Aguardar o resultado"),
    L(
        "Wait until the job finishes (up to the maximum wait). Off: return the job id at once.",
        "等待任务完成（不超过最长等待时间）。关闭时立即返回任务 ID。",
        "ジョブの完了まで待ちます（最大待機時間まで）。オフにするとすぐにジョブ ID を返します。",
        "Aguarda o job terminar (até o tempo máximo). Desligado: retorna o ID do job na hora.",
    ),
    form="form",
    default=True,
)


def MAX_WAIT(default: int = 120) -> dict[str, Any]:
    return param(
        "max_wait_seconds",
        "number",
        L("Maximum wait (seconds)", "最长等待（秒）", "最大待機時間（秒）", "Espera máxima (segundos)"),
        L(
            f"How long to wait, 10 to 420 seconds (default {default}). Work still running is returned with its id.",
            f"最长等待时间，10 到 420 秒（默认 {default}）。仍在进行的任务会连同 ID 一起返回。",
            f"待機時間は 10〜420 秒（既定 {default}）。実行中の処理は ID とともに返されます。",
            f"Quanto esperar, de 10 a 420 segundos (padrão {default}). O que ainda estiver em andamento é retornado com seu ID.",
        ),
        form="form",
        default=default,
        min=10,
        max=420,
    )


def RETURN_FILE(default: bool = True) -> dict[str, Any]:
    return param(
        "return_file",
        "boolean",
        L("Attach the files", "附加文件", "ファイルを添付", "Anexar os arquivos"),
        L(
            "Download the files Muse made and return them as Dify files (up to 150 MB each).",
            "下载 Muse 生成的文件并作为 Dify 文件返回（每个最大 150 MB）。",
            "Muse が作ったファイルをダウンロードして Dify のファイルとして返します（各 150 MB まで）。",
            "Baixa os arquivos que o Muse fez e retorna como arquivos do Dify (até 150 MB cada).",
        ),
        form="form",
        default=default,
    )


REPLY_URL = param(
    "reply_url",
    "string",
    L("Webhook URL", "Webhook 地址", "Webhook URL", "URL de webhook"),
    L(
        "Optional public https URL that receives the finished job record by POST.",
        "可选。通过 POST 接收完成后任务记录的公开 https 地址。",
        "任意。完了したジョブの記録を POST で受け取る公開 https URL。",
        "URL https pública opcional que recebe o registro do job concluído via POST.",
    ),
    form="form",
)


def PROMPT(kind: str) -> dict[str, Any]:
    if kind == "video":
        human = L(
            "What the video shows. Name the inputs as image_1, video_1, audio_1. Lines in quotes are spoken.",
            "视频内容描述。用 image_1、video_1、audio_1 指代输入文件。引号中的台词会被说出来。",
            "動画の内容。入力は image_1、video_1、audio_1 のように指定します。引用符内のセリフは話されます。",
            "O que o vídeo mostra. Cite as entradas como image_1, video_1, audio_1. Falas entre aspas são ditas.",
        )
        llm = (
            "What the video shows, up to 5000 characters. Muse makes one video of about 10 seconds with sound. Name the inputs in the prompt "
            "as image_1.., video_1.., audio_1.. in the order given; every name used must be given. Dialogue written in quotes is spoken "
            '(a talking photo: Animate image_1, she smiles and says "Hello!"). To edit a video: Edit video_1, replace the rider with the woman from image_1. '
            "Muse refuses to repeat a request the account already made: vary the prompt for each new video."
        )
    else:
        human = L(
            "What the image shows. Name the input images as image_1, image_2.",
            "图片内容描述。用 image_1、image_2 指代输入图片。",
            "画像の内容。入力画像は image_1、image_2 のように指定します。",
            "O que a imagem mostra. Cite as imagens de entrada como image_1, image_2.",
        )
        llm = (
            "What the image shows, up to 5000 characters. Muse makes one image (WebP, about 2 to 2.5 megapixels). Name the input images "
            "in the prompt as image_1, image_2.. in the order given, e.g. 'the person from image_2 wearing the jacket from image_1', "
            "'restore and colorize the old photo image_1'. Muse refuses to repeat a request the account already made: vary the prompt."
        )
    return param("prompt", "string", L("Prompt", "提示词", "プロンプト", "Prompt"), human, llm, required=True)


ASPECT_LABEL = L("Aspect ratio", "宽高比", "アスペクト比", "Proporção")
ASPECT_HUMAN = L(
    "Optional. Adds 'In exactly <ratio> aspect ratio' to the prompt (Muse has no ratio setting). Skipped when the prompt already names one.",
    "可选。在提示词前加上“In exactly <比例> aspect ratio”（Muse 没有比例参数）。提示词已写明比例时不添加。",
    "任意。プロンプトに「In exactly <比率> aspect ratio」を加えます（Muse には比率の設定がありません）。プロンプトで比率を指定済みなら追加しません。",
    "Opcional. Acrescenta 'In exactly <proporção> aspect ratio' ao prompt (o Muse não tem ajuste de proporção). Ignorado quando o prompt já cita uma.",
)
ASPECT_IMAGE = [same(r) for r in ("1:1", "16:9", "9:16", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "21:9")]
ASPECT_VIDEO = [same(r) for r in ("16:9", "9:16", "3:4")]


def ASPECT(options: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    extra = " An image-to-video job keeps the start image's shape unless a ratio is asked for." if kind == "video" else ""
    return select(
        "aspect_ratio",
        ASPECT_LABEL,
        ASPECT_HUMAN,
        options,
        f"Optional aspect ratio; the plugin adds 'In exactly <ratio> aspect ratio' to the prompt.{extra} One of: "
        + ", ".join(o["value"] for o in options)
        + ".",
    )


KIND_I18N = {
    "image": ("image", "图片", "画像", "imagem", "imagens"),
    "video": ("video", "视频", "動画", "vídeo", "vídeos"),
    "audio": ("audio", "音频", "音声", "áudio", "áudios"),
}
FILE_TYPES = {
    "image": ("JPEG, PNG or WebP", "JPEG、PNG 或 WebP", "JPEG、PNG、WebP", "JPEG, PNG ou WebP"),
    "video": ("MP4, MOV or WebM", "MP4、MOV 或 WebM", "MP4、MOV、WebM", "MP4, MOV ou WebM"),
    "audio": ("MP3, WAV, M4A or OGG", "MP3、WAV、M4A 或 OGG", "MP3、WAV、M4A、OGG", "MP3, WAV, M4A ou OGG"),
}


def INPUT_IDS(kind: str, name: str, limit: int) -> dict[str, Any]:
    en, zh, ja, pt, pts = KIND_I18N[kind]
    return param(
        name,
        "string",
        L(f"Input {en} asset IDs", f"输入{zh}资源 ID", f"入力{ja}のアセット ID", f"IDs de {pts} de entrada"),
        L(
            f"Optional asset ids of {en} files (from Upload, a job or the Library), one per line, up to {limit}. They become {kind}_1, {kind}_2.",
            f"可选。{zh}文件的资源 ID（来自上传、任务或资料库），每行一个，最多 {limit} 个。依次对应 {kind}_1、{kind}_2。",
            f"任意。{ja}ファイルのアセット ID（アップロード、ジョブ、ライブラリから）を 1 行に 1 つ、最大 {limit} 件。順に {kind}_1、{kind}_2 になります。",
            f"IDs de ativos opcionais de {pts} (de Enviar, de um job ou da Biblioteca), um por linha, até {limit}. Viram {kind}_1, {kind}_2.",
        ),
        f"Optional {en} asset ids (user:...-email:<hex>-{kind}:...), separated by new lines or commas, up to {limit}. "
        f"They are named {kind}_1, {kind}_2.. in this order; name them so in the prompt. All inputs must be on one Muse account.",
    )


def INPUT_FILES(kind: str, name: str, limit: int) -> dict[str, Any]:
    en, zh, ja, pt, pts = KIND_I18N[kind]
    return param(
        name,
        "files",
        L(f"Input {en} files", f"输入{zh}文件", f"入力{ja}ファイル", f"Arquivos de {pts} de entrada"),
        L(
            f"Optional. Or upload {en} files here ({FILE_TYPES[kind][0]}, up to 50 MB each). They come after the ids, up to {limit} in all.",
            f"可选。也可以在这里上传{zh}文件（{FILE_TYPES[kind][1]}，每个最大 50 MB）。排在 ID 之后，合计最多 {limit} 个。",
            f"任意。{ja}ファイルをここでアップロードすることもできます（{FILE_TYPES[kind][2]}、各 50 MB まで）。ID の後に続き、合計 {limit} 件まで。",
            f"Opcional. Ou envie arquivos de {pt} aqui ({FILE_TYPES[kind][3]}, até 50 MB cada). Vêm depois dos IDs, até {limit} no total.",
        ),
        f"Optional {en} files, uploaded to Muse and numbered after the ids ({kind}_N), up to {limit} in all.",
    )


CHAT_ID = param(
    "chat_id",
    "string",
    L("Chat ID", "对话 ID", "チャット ID", "ID do chat"),
    L(
        "The chat_id returned by Muse chat or List Muse chats.",
        "“Muse 对话”或“列出 Muse 对话”返回的对话 ID。",
        "「Muse とチャット」または「Muse のチャット一覧」で返された chat_id。",
        "O chat_id retornado por Chat com o Muse ou Listar chats do Muse.",
    ),
    "The chat_id from chat or list_chats, e.g. c-u12345-email:john@gmail.com-chat:...-bot:muse.",
    required=True,
)


def LIMIT(default: int, what: str) -> dict[str, Any]:
    return param(
        "limit",
        "number",
        L("Limit", "数量上限", "件数", "Limite"),
        L(
            f"Optional. How many {what} per page, 1 to 100 (default {default}).",
            f"可选。每页数量，1 到 100（默认 {default}）。",
            f"任意。1 ページの件数、1〜100（既定 {default}）。",
            f"Opcional. Quantos por página, de 1 a 100 (padrão {default}).",
        ),
        f"Optional page size, 1 to 100. Default {default}.",
        min=1,
        max=100,
    )


CURSOR = param(
    "cursor",
    "string",
    L("Cursor", "游标", "カーソル", "Cursor"),
    L(
        "Optional. The cursor of the previous page, to read the next one.",
        "可选。上一页返回的游标，用于读取下一页。",
        "任意。次のページを読むための、前のページのカーソル。",
        "Opcional. O cursor da página anterior, para ler a próxima.",
    ),
    "Optional cursor from the previous page's result, to read the next page.",
)

GEN_OUTPUT = {
    "jobid": {"type": "string"},
    "status": {"type": "string"},
    "asset_ids": {"type": "array", "items": {"type": "string"}},
    "reply": {"type": "string"},
}
CHAT_OUTPUT = {
    "chat_id": {"type": "string"},
    "status": {"type": "string"},
    "reply": {"type": "string"},
    "asset_ids": {"type": "array", "items": {"type": "string"}},
    "approval_ids": {"type": "array", "items": {"type": "string"}},
}

ASSET_TYPES = [
    opt("image", L("Images", "图片", "画像", "Imagens")),
    opt("video", L("Videos", "视频", "動画", "Vídeos")),
    opt("audio", L("Audio", "音频", "音声", "Áudio")),
    opt("document", L("Documents", "文档", "ドキュメント", "Documentos")),
    opt("web", L("Web apps", "网页应用", "Web アプリ", "Apps web")),
    opt("podcast", L("Podcasts", "播客", "ポッドキャスト", "Podcasts")),
]
ORIGINS = [
    opt("uploaded", L("Uploaded", "上传的", "アップロード", "Enviados")),
    opt("generated", L("Generated by Muse", "Muse 生成的", "Muse が生成", "Gerados pelo Muse")),
    opt("made", L("Made by the agent", "智能体制作的", "エージェントが作成", "Feitos pelo agente")),
]
DECISIONS = [
    opt("allow_once", L("Allow once", "允许一次", "1 回だけ許可", "Permitir uma vez")),
    opt("allow_always", L("Always allow this site", "始终允许此网站", "このサイトを常に許可", "Sempre permitir este site")),
    opt("deny", L("Deny", "拒绝", "拒否", "Negar")),
]

# ------------------------------------------------------------------ tools

TOOLS: list[dict[str, Any]] = []


def tool(
    name: str, label: dict[str, str], human: dict[str, str], llm: str, params: list[dict[str, Any]], output: dict[str, Any] | None = None
) -> None:
    TOOLS.append({"name": name, "label": label, "human": human, "llm": llm, "params": params, "output": output})


# --- accounts and jobs

tool(
    "list_accounts",
    L("List Muse accounts", "列出 Muse 账号", "Muse アカウント一覧", "Listar contas do Muse"),
    L(
        "List the Muse accounts connected to useapi.net, with their health, plan and weekly usage as last read.",
        "列出已连接到 useapi.net 的 Muse 账号，以及最近一次读取的状态、方案和每周用量。",
        "useapi.net に接続済みの Muse アカウントを、状態、プラン、前回読み取った週間使用量とともに一覧表示します。",
        "Lista as contas do Muse conectadas à useapi.net, com saúde, plano e uso semanal da última leitura.",
    ),
    "List the Muse accounts connected to the useapi.net Muse API: health (OK or the reason it needs attention), plan, weekly usage as last read, maxJobs, and any video limit.",
    [],
    {"emails": {"type": "array", "items": {"type": "string"}}, "healthy_emails": {"type": "array", "items": {"type": "string"}}},
)

tool(
    "get_account",
    L("Get Muse account usage", "获取 Muse 账号用量", "Muse アカウントの使用量", "Ver uso da conta do Muse"),
    L(
        "Read one Muse account live: its plan, how much of the weekly allowance is used and when it resets.",
        "实时读取某个 Muse 账号：方案、每周额度已用比例和重置时间。",
        "Muse アカウントをライブで読み取ります：プラン、週間使用枠の使用率、リセット時刻。",
        "Lê uma conta do Muse ao vivo: plano, quanto da cota semanal foi usado e quando ela renova.",
    ),
    "Read one Muse account live from Muse: plan (tier), percent of the weekly allowance used, reset time, top-up, and whether a video limit holds it.",
    [EMAIL_READ("plan and weekly usage")],
    {"plan": {"type": "string"}, "percent_used": {"type": "number"}, "resets_at": {"type": "string"}},
)

tool(
    "list_jobs",
    L("List running jobs", "列出运行中的任务", "実行中のジョブ一覧", "Listar jobs em execução"),
    L(
        "The image and video jobs running now, and how many job slots each account uses.",
        "当前正在运行的图片和视频任务，以及每个账号占用的任务槽位。",
        "実行中の画像・動画ジョブと、各アカウントが使っているジョブ枠の数。",
        "Os jobs de imagem e vídeo em execução agora e quantos slots cada conta usa.",
    ),
    "List the Muse image and video jobs running now (jobid, account, type) and each account's used and maximum job slots (maxJobs).",
    [],
    {"jobids": {"type": "array", "items": {"type": "string"}}},
)

tool(
    "get_job",
    L("Get job status", "获取任务状态", "ジョブの状態を取得", "Ver status do job"),
    L(
        "Check an image or video job, optionally wait for it, and return its file.",
        "查询图片或视频任务，可选择等待完成，并返回生成的文件。",
        "画像または動画のジョブを確認し、必要なら完了まで待ってファイルを返します。",
        "Consulta um job de imagem ou vídeo, opcionalmente aguarda e retorna o arquivo.",
    ),
    "Get a Muse job by jobid: status started / completed / failed; when completed, the asset ids, Muse's message and the files. Use it when a generation is still running.",
    [JOBID, WAIT, MAX_WAIT(120), RETURN_FILE()],
    GEN_OUTPUT,
)

# --- generation

tool(
    "generate_image",
    L("Generate image", "生成图片", "画像を生成", "Gerar imagem"),
    L(
        "Make one image with Muse from a prompt, or from up to 9 input images: combine them, edit one, or restore and colorize an old photo.",
        "用 Muse 根据提示词生成一张图片，或基于最多 9 张输入图片：合成、编辑，或修复并上色老照片。",
        "Muse でプロンプトから画像を 1 枚作成します。最大 9 枚の入力画像から合成、編集、古い写真の修復とカラー化も可能。",
        "Gera uma imagem com o Muse a partir de um prompt ou de até 9 imagens de entrada: combinar, editar ou restaurar e colorir uma foto antiga.",
    ),
    "Generate one Muse image (WebP). Text to image, or image to image with up to 9 inputs named image_1..image_9 in the prompt. Uses a little of the account's weekly Muse allowance (0 to 1 percent on the free plan). Waits up to max_wait, else returns a jobid for get_job.",
    [
        PROMPT("image"),
        ASPECT(ASPECT_IMAGE, "image"),
        INPUT_IDS("image", "images", 9),
        INPUT_FILES("image", "image_files", 9),
        EMAIL(),
        WAIT,
        MAX_WAIT(120),
        RETURN_FILE(),
        REPLY_URL,
    ],
    GEN_OUTPUT,
)

tool(
    "generate_video",
    L("Generate video", "生成视频", "動画を生成", "Gerar vídeo"),
    L(
        "Make a video of about 10 seconds with sound with Muse: from text, animate a photo (it can speak a line), or edit a video with people from your images.",
        "用 Muse 生成约 10 秒的有声视频：基于文本、让照片动起来（还能说出台词），或用你的图片中的人物编辑视频。",
        "Muse で約 10 秒の音声付き動画を作成：テキストから、写真を動かす（セリフも話せます）、画像の人物で動画を編集。",
        "Gera um vídeo de cerca de 10 segundos com som no Muse: a partir de texto, animando uma foto (ela pode falar uma fala) ou editando um vídeo com pessoas das suas imagens.",
    ),
    "Generate one Muse video, about 10 seconds, about 720p, with sound. Modes: text to video (no inputs); image to video and talking photos (image_1 plus a quoted line in the prompt); video to video edits (video_1, e.g. swap a person for someone from image_1). Inputs: up to 9 images, 3 videos and 3 audio files, named image_N, video_N, audio_N in the prompt. Uses 2 to 3 percent of the free plan's weekly Muse allowance. Waits up to max_wait (default 180 s; videos take 60 to 140 s), else returns a jobid for get_job.",
    [
        PROMPT("video"),
        ASPECT(ASPECT_VIDEO, "video"),
        INPUT_IDS("image", "images", 9),
        INPUT_FILES("image", "image_files", 9),
        INPUT_IDS("video", "videos", 3),
        INPUT_FILES("video", "video_files", 3),
        INPUT_IDS("audio", "audio", 3),
        INPUT_FILES("audio", "audio_files", 3),
        EMAIL(),
        WAIT,
        MAX_WAIT(180),
        RETURN_FILE(),
        REPLY_URL,
    ],
    GEN_OUTPUT,
)

# --- Library

tool(
    "upload_file",
    L("Upload a file to Muse", "上传文件到 Muse", "Muse にファイルをアップロード", "Enviar arquivo ao Muse"),
    L(
        "Upload an image, video or audio file (or its public https URL) to a Muse account and get its asset id.",
        "把图片、视频或音频文件（或其公开 https 地址）上传到 Muse 账号，并获得资源 ID。",
        "画像・動画・音声ファイル（または公開 https URL）を Muse アカウントにアップロードし、アセット ID を取得します。",
        "Envia um arquivo de imagem, vídeo ou áudio (ou sua URL https pública) para uma conta do Muse e retorna o ID do ativo.",
    ),
    "Upload an image (JPEG, PNG, WebP), video (MP4, MOV, WebM) or audio file (MP3, WAV, M4A, OGG), up to 50 MB, to a Muse account. Returns the asset_id to pass as an input of the job and chat tools on the same account. Uses no allowance.",
    [
        param(
            "file",
            "file",
            L("File", "文件", "ファイル", "Arquivo"),
            L(
                "The image, video or audio file, up to 50 MB.",
                "图片、视频或音频文件，最大 50 MB。",
                "画像・動画・音声ファイル（50 MB まで）。",
                "O arquivo de imagem, vídeo ou áudio, até 50 MB.",
            ),
            "The file to upload. Give this or url.",
        ),
        param(
            "url",
            "string",
            L("File URL", "文件地址", "ファイルの URL", "URL do arquivo"),
            L(
                "Or a public https URL of the file; useapi.net downloads it.",
                "或文件的公开 https 地址，由 useapi.net 下载。",
                "またはファイルの公開 https URL（useapi.net がダウンロードします）。",
                "Ou uma URL https pública do arquivo; a useapi.net faz o download.",
            ),
            "Optional public https URL of the file, used when file is empty.",
        ),
        EMAIL(),
    ],
    {"asset_id": {"type": "string"}, "email": {"type": "string"}},
)

tool(
    "list_assets",
    L("List Muse Library", "列出 Muse 资料库", "Muse ライブラリ一覧", "Listar a Biblioteca do Muse"),
    L(
        "List a Muse account's Library, newest first: images, videos, audio, documents, web apps and podcasts, with their asset ids.",
        "按时间倒序列出 Muse 账号的资料库：图片、视频、音频、文档、网页应用和播客，以及它们的资源 ID。",
        "Muse アカウントのライブラリを新しい順に一覧表示します：画像、動画、音声、ドキュメント、Web アプリ、ポッドキャストとそのアセット ID。",
        "Lista a Biblioteca de uma conta do Muse, mais recentes primeiro: imagens, vídeos, áudios, documentos, apps web e podcasts, com os IDs.",
    ),
    "List the Muse Library of an account, newest first, with asset ids, types, origins (uploaded / generated / made) and names. Page with cursor.",
    [
        EMAIL_READ("Library"),
        select(
            "type",
            L("Type", "类型", "種類", "Tipo"),
            L(
                "Optional. Only this kind of item.",
                "可选。只列出此类项目。",
                "任意。この種類だけを表示。",
                "Opcional. Só este tipo de item.",
            ),
            ASSET_TYPES,
        ),
        select(
            "origin",
            L("Origin", "来源", "作成元", "Origem"),
            L(
                "Optional. Only media files of this origin.",
                "可选。只列出此来源的媒体文件。",
                "任意。この作成元のメディアだけを表示。",
                "Opcional. Só mídias desta origem.",
            ),
            ORIGINS,
        ),
        LIMIT(50, "items"),
        CURSOR,
    ],
    {"asset_ids": {"type": "array", "items": {"type": "string"}}, "cursor": {"type": "string"}},
)

tool(
    "get_asset",
    L("Download a Muse file", "下载 Muse 文件", "Muse のファイルをダウンロード", "Baixar arquivo do Muse"),
    L(
        "Download an image, video, audio file, document or web app from the Muse Library by its asset id, as a Dify file.",
        "按资源 ID 从 Muse 资料库下载图片、视频、音频、文档或网页应用，作为 Dify 文件返回。",
        "アセット ID で Muse ライブラリから画像・動画・音声・ドキュメント・Web アプリを Dify のファイルとしてダウンロードします。",
        "Baixa uma imagem, vídeo, áudio, documento ou app web da Biblioteca do Muse pelo ID, como arquivo do Dify.",
    ),
    "Download one Muse Library item by asset id and return it as a file: an image, video or audio file, a document (format=pdf turns md, txt or html into a PDF), a web app as one HTML file, or a podcast as MP3.",
    [
        param(
            "asset_id",
            "string",
            L("Asset ID", "资源 ID", "アセット ID", "ID do ativo"),
            L(
                "The asset id from a job, a chat, Upload or the Library.",
                "来自任务、对话、上传或资料库的资源 ID。",
                "ジョブ、チャット、アップロード、ライブラリのアセット ID。",
                "O ID do ativo de um job, chat, envio ou da Biblioteca.",
            ),
            "The asset id to download, e.g. user:12345-email:<hex>-video:....mp4.",
            required=True,
        ),
        select(
            "format",
            L("Format", "格式", "形式", "Formato"),
            L(
                "Optional. PDF turns an md, txt or html document into a PDF.",
                "可选。PDF 会把 md、txt 或 html 文档转换为 PDF。",
                "任意。PDF を選ぶと md・txt・html のドキュメントを PDF にします。",
                "Opcional. PDF converte um documento md, txt ou html em PDF.",
            ),
            [opt("pdf", L("PDF", "PDF", "PDF", "PDF"))],
        ),
    ],
    {"mime_type": {"type": "string"}},
)

# --- Muse chat

CHAT_WAIT = param(
    "wait",
    "boolean",
    L("Wait for the answer", "等待回答", "回答を待つ", "Aguardar a resposta"),
    L(
        "Wait until Muse's answer ends or it asks for permission (up to the maximum wait).",
        "等待 Muse 回答结束或请求权限（不超过最长等待时间）。",
        "Muse の回答が終わるか許可を求めるまで待ちます（最大待機時間まで）。",
        "Aguarda a resposta do Muse terminar ou um pedido de permissão (até o tempo máximo).",
    ),
    form="form",
    default=True,
)

tool(
    "chat",
    L("Muse chat", "Muse 对话", "Muse とチャット", "Chat com o Muse"),
    L(
        "Talk to Muse, Meta's AI agent: it answers, researches the web, writes documents and code, and makes images and videos. Start a chat or continue one.",
        "与 Meta 的 AI 智能体 Muse 对话：它会回答问题、上网调研、写文档和代码，并生成图片和视频。可开始新对话或继续已有对话。",
        "Meta の AI エージェント Muse と会話：回答、Web 調査、ドキュメントやコードの作成、画像や動画の作成ができます。新しいチャットも続きも可能。",
        "Converse com o Muse, o agente de IA da Meta: ele responde, pesquisa na web, escreve documentos e código e cria imagens e vídeos. Comece ou continue um chat.",
    ),
    "Send a message to Muse, Meta's AI agent at muse.ai (it talks, researches the web, writes and runs code, writes documents, makes images and videos). Without chat_id a new chat starts; with chat_id the message continues it. Give files as asset ids or workspace paths; Muse sees them as image_1, video_1, audio_1, file_1 in order. Returns Muse's reply, the files it made (asset ids, attached as files), quick-reply options and any permission request: then ask the user and call answer_approval. Uses the account's weekly Muse allowance.",
    [
        param(
            "message",
            "string",
            L("Message", "消息", "メッセージ", "Mensagem"),
            L("What you say to Muse.", "你要对 Muse 说的话。", "Muse へのメッセージ。", "O que você diz ao Muse."),
            "What to say to Muse, up to 5000 characters.",
            required=True,
        ),
        param(
            "chat_id",
            "string",
            L("Chat ID", "对话 ID", "チャット ID", "ID do chat"),
            L(
                "Optional. Continue this chat. Empty: start a new chat.",
                "可选。继续此对话。留空：开始新对话。",
                "任意。このチャットを続けます。空欄なら新しいチャット。",
                "Opcional. Continua este chat. Vazio: começa um novo.",
            ),
            "Optional chat_id from an earlier chat or list_chats, to continue that chat. Leave empty for a new chat.",
        ),
        param(
            "files",
            "string",
            L("File asset IDs or paths", "文件资源 ID 或路径", "ファイルのアセット ID またはパス", "IDs ou caminhos de arquivos"),
            L(
                "Optional asset ids (images, videos, audio, documents) or workspace paths, one per line.",
                "可选。资源 ID（图片、视频、音频、文档）或工作区路径，每行一个。",
                "任意。アセット ID（画像・動画・音声・ドキュメント）またはワークスペースのパスを 1 行に 1 つ。",
                "IDs de ativos (imagens, vídeos, áudios, documentos) ou caminhos do workspace opcionais, um por linha.",
            ),
            "Optional files for Muse, one per line: asset ids (up to 9 images, 3 videos, 3 audio) and document asset ids or workspace paths (up to 10). Muse sees them as image_1, video_1, audio_1, file_1 in this order. They must be on the chat's account.",
        ),
        param(
            "upload_files",
            "files",
            L("Files to upload", "要上传的文件", "アップロードするファイル", "Arquivos para enviar"),
            L(
                "Optional image, video or audio files, uploaded to the chat's account and added after the ids (up to 50 MB each).",
                "可选。图片、视频或音频文件，会上传到对话所在账号并排在 ID 之后（每个最大 50 MB）。",
                "任意。画像・動画・音声ファイル。チャットのアカウントにアップロードされ、ID の後に追加されます（各 50 MB まで）。",
                "Arquivos opcionais de imagem, vídeo ou áudio, enviados à conta do chat e adicionados depois dos IDs (até 50 MB cada).",
            ),
            "Optional image, video or audio files, uploaded to Muse and added after the ids in files.",
        ),
        EMAIL(),
        CHAT_WAIT,
        MAX_WAIT(120),
        RETURN_FILE(),
    ],
    CHAT_OUTPUT,
)

tool(
    "get_chat",
    L("Get Muse chat", "获取 Muse 对话", "Muse のチャットを取得", "Ver chat do Muse"),
    L(
        "Read a Muse chat: its status, Muse's latest answer, the files it made and any permission request.",
        "读取 Muse 对话：状态、Muse 的最新回答、生成的文件以及权限请求。",
        "Muse のチャットを読み取ります：状態、最新の回答、作成されたファイル、許可リクエスト。",
        "Lê um chat do Muse: status, a última resposta do Muse, os arquivos que ele fez e pedidos de permissão.",
    ),
    "Read a Muse chat: Muse's answer to the latest user message, its files, quick replies and pending permission requests. With wait=true, waits until the running answer ends (up to max_wait). Use it after chat returned status running.",
    [
        CHAT_ID,
        param(
            "wait",
            "boolean",
            L("Wait for the answer", "等待回答", "回答を待つ", "Aguardar a resposta"),
            L(
                "Wait until the running answer ends (up to the maximum wait).",
                "等待正在进行的回答结束（不超过最长等待时间）。",
                "実行中の回答が終わるまで待ちます（最大待機時間まで）。",
                "Aguarda a resposta em andamento terminar (até o tempo máximo).",
            ),
            "true to wait until Muse's running answer ends.",
            default=False,
        ),
        MAX_WAIT(120),
        RETURN_FILE(),
    ],
    CHAT_OUTPUT,
)

tool(
    "answer_approval",
    L(
        "Answer a Muse permission request",
        "答复 Muse 的权限请求",
        "Muse の許可リクエストに回答",
        "Responder a um pedido de permissão do Muse",
    ),
    L(
        "Allow or deny what Muse asks permission for, for example sharing information with a website, then read the rest of its answer.",
        "允许或拒绝 Muse 请求的操作（例如向某个网站发送信息），然后读取它后续的回答。",
        "Muse が許可を求めている操作（Web サイトへの情報送信など）を許可または拒否し、続きの回答を読み取ります。",
        "Permite ou nega o que o Muse pede permissão para fazer (por exemplo, compartilhar dados com um site) e lê o resto da resposta.",
    ),
    "Answer Muse's permission request (status waiting_for_approval). allow_once: allow this request; allow_always: allow this site from now on for the whole Muse account; deny: refuse, Muse goes on without it. Ask the user first. Then waits for the rest of the answer.",
    [
        CHAT_ID,
        param(
            "approval_id",
            "string",
            L("Approval ID", "请求 ID", "リクエスト ID", "ID do pedido"),
            L(
                "Optional when only one request waits in the chat.",
                "对话中只有一个待答复请求时可省略。",
                "チャットで待っているリクエストが 1 つだけなら省略できます。",
                "Opcional quando só um pedido aguarda no chat.",
            ),
            "The approval_id from chat or get_chat. Optional when exactly one request waits.",
        ),
        select(
            "decision",
            L("Decision", "决定", "回答", "Decisão"),
            L(
                "Allow once, always allow this site, or deny.",
                "允许一次、始终允许此网站或拒绝。",
                "1 回だけ許可、このサイトを常に許可、拒否。",
                "Permitir uma vez, sempre permitir este site ou negar.",
            ),
            DECISIONS,
            "allow_once, allow_always or deny.",
        )
        | {"required": True},
        CHAT_WAIT,
        MAX_WAIT(120),
        RETURN_FILE(),
    ],
    CHAT_OUTPUT,
)

tool(
    "list_chats",
    L("List Muse chats", "列出 Muse 对话", "Muse のチャット一覧", "Listar chats do Muse"),
    L(
        "List the chats of a Muse account, newest first, including the ones the jobs created.",
        "按时间倒序列出 Muse 账号的对话，包括任务创建的对话。",
        "Muse アカウントのチャットを新しい順に一覧表示します（ジョブが作ったチャットも含む）。",
        "Lista os chats de uma conta do Muse, mais recentes primeiro, incluindo os criados pelos jobs.",
    ),
    "List the Muse chats of an account, newest first: chat_id, title, status and last update. Every job is a chat too. Page with cursor.",
    [EMAIL_READ("chats"), LIMIT(50, "chats"), CURSOR],
    {"chat_ids": {"type": "array", "items": {"type": "string"}}, "cursor": {"type": "string"}},
)
