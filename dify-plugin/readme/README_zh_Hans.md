# Meta Muse，由 useapi.net 提供

**作者：** useapi · **版本：** 0.1.0 · **类型：** 工具 · **源代码：** https://github.com/useapi/muse-api/tree/main/dify-plugin · **联系方式：** support@useapi.net

在 Dify 的工作流、Chatflow 和 Agent 中使用 Meta 的 AI 智能体 Muse（[muse.ai](https://muse.ai)）。用文本生成约 10 秒的有声视频，让照片动起来并说出一句台词，用你图片中的人物编辑视频，根据文本或最多 9 张输入图片生成图片，还可以与 Muse 智能体对话：它会上网调研、写文档和代码，并为你生成文件。图片、视频和文档以 Dify 文件形式返回。

**在你自己的 Muse 账号上运行，免费方案即可。** 连接多个 Muse 账号并把邮箱留空，useapi.net 会把每个新任务发给健康、有剩余额度且有空闲任务槽位的账号，所有账号的每周额度可以叠加使用。详见[多个 Muse 账号](#多个-muse-账号)。

> 本插件调用 useapi.net 提供的 [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin)，这是第三方 API，并非由 Meta 开发，与 Meta 无关联，也未获得 Meta 认可。使用前需要：useapi.net 订阅（每月 15 美元，包含 useapi.net 的全部 API），以及一个 muse.ai 上的 Muse 账号。截至 2026 年 11 月 25 日，Muse 在美国、加拿大、日本、新加坡和澳大利亚提供，请在其中之一注册账号；账号添加后，可以在任何地方调用 API。

## Muse 方案与每周额度

Muse 按周计量每个账号的用量。任务和对话消耗所在账号的额度，上传和下载不消耗。

| Muse 方案 | 价格 | 每周额度 |
|---|---|---|
| Free | $0 | 未公布 |
| Power | 每月 $20 | 5 亿 Muse tokens |
| Maximum | 每月 $100 | 30 亿 Muse tokens |

来源：Meta [About Muse subscriptions](https://www.meta.com/help/subscriptions/1021145227643680/)，2026 年 11 月，见 useapi.net 的 [Muse 设置](https://useapi.net/docs/start-here/setup-muse#usage-limits)。不同地区可能不同。在 useapi.net 的测试中，免费方案下一个视频消耗每周额度的 2% 到 3%，一张图片 0% 到 1%；Meta 未公布每个任务的消耗。“获取 Muse 账号用量”可查看已用比例和重置时间。表中只列 Muse 方案的费用，useapi.net 订阅（每月 15 美元）另计。

## 快速开始

1. **获取 useapi.net API 令牌**：订阅后复制令牌，见 [Setup useapi.net](https://useapi.net/docs/start-here/setup-useapi?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin)。
2. **连接 Muse 账号**：按照 [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) 操作。账号需要支持邮箱加密码登录，在 muse.ai 完成引导（包括 Meta 的年龄验证）并在那里生成过一张图片。该账号只用于 API，不要同时使用其他自动化工具。
3. **安装并授权插件，然后生成视频**：在 [Dify 插件市场](https://marketplace.dify.ai/plugins/useapi/muse_useapi)安装，或在“插件 > 安装插件 > 本地插件包”中上传 [GitHub releases](https://github.com/useapi/muse-api/releases) 里的 `.difypkg`。在“工具”中打开 “Meta Muse，由 useapi.net 提供”，点击授权，粘贴令牌并保存。然后在工作流中添加“生成视频”，提示词写 `A paper boat floating on a calm pond at sunrise, a frog on the bank says "Bon voyage!"`，宽高比选 16:9 并运行，`.mp4` 会以文件形式返回。

| 凭据 | 必填 | 说明 |
|---|:-:|---|
| useapi.net API 令牌 | 是 | 第 1 步获得的令牌，由 Dify 加密保存。 |
| 默认 Muse 账号邮箱 | 否 | 留空则由 useapi.net 选择账号。只有要把所有工具固定到一个 Muse 账号时才填写。 |

保存凭据时会调用一次 `GET /accounts`，确认令牌有效且至少已连接一个 Muse 账号，不会调用 Muse。

插件只连接 `https://api.useapi.net/v1/muse`（令牌放在 `Authorization: Bearer` 请求头中）。生成的文件也从同一 API（`GET /assets/{assetId}`）下载，由它从你的 Muse 账号中传输。自托管的 Dify 需要能访问 `api.useapi.net`，无需代理、Webhook 或入站连接。

## 多个 Muse 账号

每个 useapi.net 订阅可添加 3 个 Muse 账号，添加方式与第一个相同（[Setup Muse](https://useapi.net/docs/start-here/setup-muse)）。“列出 Muse 账号”会显示每个账号的状态、方案和每周用量，“列出运行中的任务”显示每个账号占用的任务槽位。

**如何选择账号**：邮箱留空且任务没有输入文件时，useapi.net 会把任务发给健康、有剩余额度且有空闲任务槽位（`maxJobs`，默认 10）的账号。视频任务还会跳过已达到 Muse 24 小时视频上限的账号。每周额度用完的账号在重置前会被跳过。

**输入文件决定账号**：你上传的文件或 Muse 生成的文件都存放在某一个 Muse 账号上，同一任务或对话的所有输入必须在同一账号上。因此带输入资源 ID 的请求会在这些文件所在的账号上运行，附加的文件也会上传到该账号。对话会一直在开始时的账号上进行，请用 `chat_id` 继续。

## 工具

共 13 个工具。资源 ID 形如 `user:12345-email:<hex>-video:<name>.mp4`，可作为变量在节点间传递。

| 工具 | 名称 | 接口 |
|---|---|---|
| `generate_image` | 生成图片 | `POST /jobs/image` |
| `generate_video` | 生成视频 | `POST /jobs/video` |
| `get_job` | 获取任务状态 | `GET /jobs/{jobid}` |
| `list_jobs` | 列出运行中的任务 | `GET /jobs` |
| `chat` | Muse 对话 | `POST /chats`、`POST /chats/{chatId}/messages`、`GET /chats/{chatId}` |
| `get_chat` | 获取 Muse 对话 | `GET /chats/{chatId}` |
| `answer_approval` | 答复 Muse 的权限请求 | `POST /chats/{chatId}/approvals/{approvalId}` |
| `list_chats` | 列出 Muse 对话 | `GET /chats` |
| `upload_file` | 上传文件到 Muse | `POST /assets` |
| `list_assets` | 列出 Muse 资料库 | `GET /assets` |
| `get_asset` | 下载 Muse 文件 | `GET /assets/{assetId}` |
| `list_accounts` | 列出 Muse 账号 | `GET /accounts` |
| `get_account` | 获取 Muse 账号用量 | `GET /accounts/{email}` |

Muse 是智能体，不是固定的生成器：没有模型、分辨率或时长设置，请在提示词中描述需求。

- **生成图片**：一张 WebP 图片，约 200 万到 250 万像素。可用最多 9 张输入图片（在提示词中写作 `image_1` 到 `image_9`）合成场景、编辑图片，或修复并上色老照片。
- **生成视频**：一个约 10 秒、约 720p 的有声 MP4。支持文本生成视频、图片生成视频（引号中的台词会被说出来，即“会说话的照片”）以及视频编辑。输入最多 9 张图片、3 个视频和 3 个音频，写作 `image_N`、`video_N`、`audio_N`。
- **宽高比**：该选项会在提示词前加上 `In exactly <比例> aspect ratio`，这是 Muse 最能遵循的写法。
- **输入**：可以是资源 ID，也可以是 Dify 文件（插件会先上传）：JPEG、PNG、WebP 图片，MP4、MOV、WebM 视频，MP3、WAV、M4A、OGG 音频，每个最大 50 MB。
- **重复的提示词**：Muse 会记住账号已经做过的内容（跨对话）。在同一账号上再次发送相同的提示词可能被拒绝（`409`），不会生成任何内容。每次请换一种写法，或换一个账号。

输出包括：可读的文本摘要（Agent 读取的内容）、JSON、文件（超过 150 MB 的不附加）以及变量 `jobid`、`status`、`asset_ids`、`reply`、`chat_id`、`approval_ids`。

## 等待与限制

- **Dify 的 600 秒限制**：生成工具提交任务后每 10 秒查询一次，默认图片等待 120 秒、视频 180 秒。未完成时返回 `jobid`，可用“获取任务状态”继续查询。工作流中“最长等待”可设为最多 420 秒。任务记录保留 7 天。
- **耗时**：在 useapi.net 的测试中，图片 20 到 60 秒，视频 60 到 140 秒。
- **任务槽位**：每个 Muse 账号同时最多运行 `maxJobs` 个任务（默认 10）。对话和上传不占用槽位。
- **视频上限**：除每周额度外，Muse 还限制账号 24 小时内的视频数量。达到后该账号在一小时内不接视频任务，图片任务不受影响。
- **权限请求**：智能体在某些操作前（例如向网站发送信息）会请求许可。对话返回 `waiting_for_approval` 和 `approval_id`，请在过期前用“答复 Muse 的权限请求”回答。

## 故障排查

| 代码 | 含义 | 处理方法 |
|---|---|---|
| 400 | 请求有误，例如提示词提到 `image_2` 但没有提供第二张图片，或尚未连接 Muse 账号。 | 按提示修改，或用 [Setup Muse](https://useapi.net/docs/start-here/setup-muse) 连接账号。 |
| 401 | useapi.net 令牌错误。 | 检查插件凭据中的令牌。 |
| 402 | useapi.net 订阅未生效。 | 续订：[subscription](https://useapi.net/docs/subscription)。 |
| 403 | Muse 拒绝生成（消息中有它的原话），Meta 在该账号所在地区关闭了视频，或 ID 属于其他 API 令牌。或者 Muse 请求了权限。 | 修改提示词或输入，原样重发没有用。视频请换一个账号。如果 Muse 请求了权限，请以 Muse 聊天方式运行，并用 `answer_approval` 回答。 |
| 404 | 账号未连接，或任务、对话、文件已不存在。 | 用 [Setup Muse](https://useapi.net/docs/start-here/setup-muse) 连接账号。 |
| 409 | Muse 表示该账号已经做过这个请求，因此没有生成任何内容；或权限请求已被答复。 | 修改提示词，或换一个账号。 |
| 410 | 任务已过期。 | 任务记录保留 7 天。 |
| 412 | 该账号（或所有账号）的每周 Muse 额度已用完。 | 等待重置（见“获取 Muse 账号用量”），或连接其他账号。 |
| 429 | 任务槽位已满、Muse 暂时限制该账号，或账号达到 Muse 的 24 小时视频上限。 | 按消息中的时间重试，或把邮箱留空让其他账号处理。 |
| 502、504 | Muse 返回错误或未按时完成，文件可能已经生成。 | 再次运行前先查看“获取任务状态”或“列出 Muse 对话”。 |
| 503 | 无法连接 Muse，或这次生成失败。 | 再运行一次，同样的提示词通常下次就能成功。 |
| 596 | 账号需要处理：Meta 要求安全验证，或 Muse 拒绝重新登录。或者 Muse 收回了账号的计算机。 | 在浏览器中登录一次 muse.ai，然后用 [Setup Muse](https://useapi.net/docs/start-here/setup-muse) 重新添加账号。如果 Muse 收回了账号的计算机，请联系 Muse 支持恢复，然后再重新添加账号。 |

## 费用

- 插件免费。
- useapi.net：每月 15 美元，包含 useapi.net 的全部 API。
- Meta：你自己的 Muse 方案（含免费方案）。任务和对话消耗其每周额度。

## 隐私

插件只向 `api.useapi.net` 发送请求，不存储任何数据。详见 [PRIVACY.md](../PRIVACY.md) 和 useapi.net 的[条款与隐私政策](https://useapi.net/docs/legal)。

## 支持

- API 文档：https://useapi.net/docs/api-muse-v1
- 示例与插件源代码：https://github.com/useapi/muse-api
- 邮件 support@useapi.net，或在 [Discord](https://discord.gg/w28uK3cnmF)、[Telegram](https://t.me/use_api) 提问。
