# Meta Muse by useapi.net

**作者：** useapi · **バージョン：** 0.1.0 · **種類：** ツール · **ソース：** https://github.com/useapi/muse-api/tree/main/dify-plugin · **連絡先：** support@useapi.net

Meta の AI エージェント Muse（[muse.ai](https://muse.ai)）を、Dify のワークフロー、チャットフロー、エージェントから使えます。テキストから約 10 秒の音声付き動画を作り、写真を動かして写っている人にセリフを話させ、画像の人物で動画を編集し、テキストや最大 9 枚の入力画像から画像を作り、Muse エージェントとチャットできます（Web 調査、ドキュメントやコードの作成、ファイルの作成も行います）。画像、動画、ドキュメントは Dify のファイルとして返ります。

**ご自身の Muse アカウントで動き、無料プランでも使えます。** 複数の Muse アカウントを接続してメールを空欄にすると、useapi.net が新しいジョブを、正常で使用枠が残り、ジョブ枠が空いているアカウントに送ります。すべてのアカウントの週間使用枠を合わせて使えます。[複数の Muse アカウント](#複数の-muse-アカウント)をご覧ください。

> このプラグインは useapi.net の [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) を呼び出します。これはサードパーティ API で、Meta が作成したものではなく、Meta とは提携しておらず、Meta の承認も受けていません。useapi.net のサブスクリプション（月額 15 ドル、useapi.net の全 API が対象）と muse.ai の Muse アカウントが必要です。Muse は 2026 年 11 月 25 日時点で米国、カナダ、日本、シンガポール、オーストラリアで提供されているため、いずれかでアカウントを作成してください。追加後はどこからでも API を呼び出せます。

## Muse のプランと週間使用枠

Muse はアカウントごとに週単位で使用量を計測します。ジョブとチャットは実行したアカウントの使用枠を使い、アップロードとダウンロードは使いません。

| Muse プラン | 料金 | 週間使用枠 |
|---|---|---|
| Free | $0 | 非公開 |
| Power | 月額 $20 | 5 億 Muse トークン |
| Maximum | 月額 $100 | 30 億 Muse トークン |

出典：Meta [About Muse subscriptions](https://www.meta.com/help/subscriptions/1021145227643680/)、2026 年 11 月（useapi.net の [Muse セットアップ](https://useapi.net/docs/start-here/setup-muse#usage-limits)に掲載）。地域によって異なる場合があります。useapi.net のテストでは、無料プランで動画 1 本が週間使用枠の 2〜3%、画像 1 枚が 0〜1% でした。Meta はジョブごとの消費量を公開していません。「Muse アカウントの使用量」で使用率とリセット時刻を確認できます。表は Muse プランの費用のみで、useapi.net のサブスクリプション（月額 15 ドル）は別です。

## クイックスタート

1. **useapi.net の API トークンを取得**：サブスクライブしてトークンをコピーします。[Setup useapi.net](https://useapi.net/docs/start-here/setup-useapi?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) を参照。
2. **Muse アカウントを接続**：[Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) に従います。アカウントにはメールとパスワードでのサインイン、muse.ai でのオンボーディング完了（Meta の年齢確認を含む）、そこでの画像 1 枚の作成が必要です。API 専用にし、他の自動化ツールは使わないでください。
3. **プラグインをインストールして認証し、動画を作成**：[Dify マーケットプレイス](https://marketplace.dify.ai/plugins/useapi/muse_useapi)からインストールするか、[GitHub releases](https://github.com/useapi/muse-api/releases) の `.difypkg` を「プラグイン > プラグインをインストール > ローカルパッケージファイル」からアップロードします。「ツール」で「Meta Muse by useapi.net」を開き、認証をクリックしてトークンを貼り付けて保存します。次にワークフローに「動画を生成」を追加し、プロンプト `A paper boat floating on a calm pond at sunrise, a frog on the bank says "Bon voyage!"`、アスペクト比 16:9 で実行すると、`.mp4` がファイルとして返ります。

| 認証情報 | 必須 | 内容 |
|---|:-:|---|
| useapi.net API トークン | はい | 手順 1 のトークン。Dify が暗号化して保存します。 |
| 既定の Muse アカウントのメール | いいえ | 空欄なら useapi.net がアカウントを選びます。すべてのツールを 1 つの Muse アカウントに固定したい場合のみ入力します。 |

認証情報の保存時に `GET /accounts` を 1 回呼び、トークンが有効で Muse アカウントが 1 つ以上接続されていることを確認します。Muse は呼び出しません。

プラグインは `https://api.useapi.net/v1/muse` にのみ接続し、トークンは `Authorization: Bearer` ヘッダーで送ります。完成したファイルも同じ API（`GET /assets/{assetId}`）からダウンロードし、API がご自身の Muse アカウントから転送します。セルフホストの Dify には `api.useapi.net` への HTTPS 接続が必要です。プロキシ、Webhook、受信接続は不要です。

## 複数の Muse アカウント

useapi.net のサブスクリプション 1 つにつき Muse アカウントを 3 つ追加できます。追加方法は最初のアカウントと同じです（[Setup Muse](https://useapi.net/docs/start-here/setup-muse)）。「Muse アカウント一覧」で各アカウントの状態、プラン、週間使用量を、「実行中のジョブ一覧」で各アカウントのジョブ枠の使用数を確認できます。

**アカウントの選び方**：メールが空欄で入力ファイルのないジョブは、正常で使用枠が残り、ジョブ枠（`maxJobs`、既定 10）が空いているアカウントに送られます。動画ジョブは、Muse の 24 時間の動画上限に達したアカウントも避けます。週間使用枠を使い切ったアカウントはリセットまで使われません。

**入力ファイルがアカウントを決めます**：アップロードしたファイルや Muse が作ったファイルは 1 つの Muse アカウントにあり、1 つのジョブやチャットの入力はすべて同じアカウントにある必要があります。そのため入力のアセット ID があるリクエストはそのアカウントで実行され、添付ファイルもそのアカウントにアップロードされます。チャットは開始したアカウントで続くので、`chat_id` で続けてください。

## ツール

13 個のツール。アセット ID は `user:12345-email:<hex>-video:<name>.mp4` の形式で、変数としてノード間で受け渡せます。

| ツール | 表示名 | エンドポイント |
|---|---|---|
| `generate_image` | 画像を生成 | `POST /jobs/image` |
| `generate_video` | 動画を生成 | `POST /jobs/video` |
| `get_job` | ジョブの状態を取得 | `GET /jobs/{jobid}` |
| `list_jobs` | 実行中のジョブ一覧 | `GET /jobs` |
| `chat` | Muse とチャット | `POST /chats`、`POST /chats/{chatId}/messages`、`GET /chats/{chatId}` |
| `get_chat` | Muse のチャットを取得 | `GET /chats/{chatId}` |
| `answer_approval` | Muse の許可リクエストに回答 | `POST /chats/{chatId}/approvals/{approvalId}` |
| `list_chats` | Muse のチャット一覧 | `GET /chats` |
| `upload_file` | Muse にファイルをアップロード | `POST /assets` |
| `list_assets` | Muse ライブラリ一覧 | `GET /assets` |
| `get_asset` | Muse のファイルをダウンロード | `GET /assets/{assetId}` |
| `list_accounts` | Muse アカウント一覧 | `GET /accounts` |
| `get_account` | Muse アカウントの使用量 | `GET /accounts/{email}` |

Muse は固定の生成器ではなくエージェントです。モデル、解像度、長さの設定はなく、プロンプトで指示します。

- **画像を生成**：WebP 画像 1 枚、約 200〜250 万画素。最大 9 枚の入力画像（プロンプトでは `image_1`〜`image_9`）で合成、編集、古い写真の修復とカラー化ができます。
- **動画を生成**：約 10 秒・約 720p の音声付き MP4 を 1 本。テキストから、画像から（引用符内のセリフが話される「話す写真」）、動画の編集。入力は画像 9 枚、動画 3 本、音声 3 つまでで、`image_N`、`video_N`、`audio_N` と書きます。
- **アスペクト比**：この設定はプロンプトに `In exactly <比率> aspect ratio` を加えます。Muse が最もよく従う書き方です。
- **入力**：アセット ID、または Dify のファイル（先にアップロードします）：JPEG・PNG・WebP 画像、MP4・MOV・WebM 動画、MP3・WAV・M4A・OGG 音声、各 50 MB まで。
- **同じプロンプトの繰り返し**：Muse はアカウントで作ったものをチャットをまたいで覚えています。同じアカウントで同じプロンプトを再送すると `409` で断られ、何も作られないことがあります。毎回言い回しを変えるか、別のアカウントで実行してください。

出力：読みやすいテキスト（エージェントが読む内容）、JSON、ファイル（150 MB を超えるものは添付しません）、変数 `jobid`、`status`、`asset_ids`、`reply`、`chat_id`、`approval_ids`。

## 待機と制限

- **Dify の 600 秒制限**：生成ツールはジョブを送信して 10 秒ごとに確認し、既定では画像 120 秒、動画 180 秒で返ります。終わっていなければ `jobid` を返すので、「ジョブの状態を取得」で続きを確認します。ワークフローでは「最大待機時間」を 420 秒まで上げられます。ジョブの記録は 7 日間保存されます。
- **所要時間**：useapi.net のテストでは画像 20〜60 秒、動画 60〜140 秒。
- **ジョブ枠**：各 Muse アカウントで同時に実行できるジョブは `maxJobs` 件まで（既定 10）。チャットとアップロードは枠を使いません。
- **動画の上限**：週間使用枠とは別に、Muse は 24 時間の動画数を制限します。上限に達したアカウントは 1 時間動画ジョブを受けません。画像ジョブは使えます。
- **許可リクエスト**：エージェントは Web サイトへの情報送信などの前に許可を求めます。チャットが `waiting_for_approval` と `approval_id` を返したら、期限内に「Muse の許可リクエストに回答」で答えてください。

## トラブルシューティング

| コード | 意味 | 対処 |
|---|---|---|
| 400 | リクエストが不正です。例：プロンプトに `image_2` があるのに 2 枚目の画像がない、Muse アカウントが未接続。 | メッセージに従って修正するか、[Setup Muse](https://useapi.net/docs/start-here/setup-muse) でアカウントを接続します。 |
| 401 | useapi.net のトークンが間違っています。 | プラグインの認証情報を確認します。 |
| 402 | useapi.net のサブスクリプションが有効ではありません。 | 更新します：[subscription](https://useapi.net/docs/subscription)。 |
| 403 | Muse が作成を断った（本人の言葉がメッセージにあります）、Meta がそのアカウントの地域で動画を止めた、または ID が別の API トークンのものです。あるいは Muse が許可を求めました。 | プロンプトか入力を変えてください。同じ内容の再送では解決しません。動画は別のアカウントで。Muse が許可を求めた場合は、Muse チャットとして実行し、`answer_approval` で答えてください。 |
| 404 | アカウントが未接続、またはジョブ・チャット・ファイルがもうありません。 | [Setup Muse](https://useapi.net/docs/start-here/setup-muse) でアカウントを接続します。 |
| 409 | Muse がこのリクエストはアカウントで作成済みだとして何も作りませんでした。または許可リクエストに回答済みです。 | プロンプトを変えるか、別のアカウントで実行します。 |
| 410 | ジョブの期限が切れました。 | ジョブの記録は 7 日間保存されます。 |
| 412 | アカウント（またはすべてのアカウント）の週間使用枠を使い切りました。 | リセットを待つ（「Muse アカウントの使用量」で確認）か、別のアカウントを接続します。 |
| 429 | ジョブ枠が満杯、Muse が一時的に制限中、または 24 時間の動画上限に達しました。 | メッセージの時刻以降に再試行するか、メールを空欄にして別のアカウントに任せます。 |
| 502、504 | Muse がエラーを返した、または時間内に終わりませんでした。ファイルはできている可能性があります。 | 再実行の前に「ジョブの状態を取得」か「Muse のチャット一覧」を確認します。 |
| 503 | Muse に接続できない、または今回は作成に失敗しました。 | もう一度実行します。同じプロンプトで次はたいてい成功します。 |
| 596 | アカウントに対応が必要です：Meta のセキュリティチェック、または Muse が再サインインを拒否しました。あるいは Muse がアカウントのコンピューターを取り上げました。 | ブラウザで一度 muse.ai にサインインし、[Setup Muse](https://useapi.net/docs/start-here/setup-muse) でアカウントを追加し直します。コンピューターを取り上げられた場合は、Muse サポートに復旧を依頼してから、アカウントを追加し直してください。 |

## 費用

- プラグインは無料です。
- useapi.net：月額 15 ドル（useapi.net の全 API が対象）。
- Meta：ご自身の Muse プラン（無料プランを含む）。ジョブとチャットは週間使用枠を使います。

## プライバシー

プラグインは `api.useapi.net` にのみリクエストを送り、データを保存しません。詳細は [PRIVACY.md](../PRIVACY.md) と useapi.net の[利用規約とプライバシーポリシー](https://useapi.net/docs/legal)をご覧ください。

## サポート

- API リファレンス：https://useapi.net/docs/api-muse-v1
- サンプルとプラグインのソース：https://github.com/useapi/muse-api
- メール support@useapi.net、または [Discord](https://discord.gg/w28uK3cnmF)、[Telegram](https://t.me/use_api) へどうぞ。
