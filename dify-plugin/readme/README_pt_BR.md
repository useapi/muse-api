# Meta Muse por useapi.net

**Autor:** useapi · **Versão:** 0.1.0 · **Tipo:** ferramenta · **Código-fonte:** https://github.com/useapi/muse-api/tree/main/dify-plugin · **Contato:** support@useapi.net

Use o Muse, o agente de IA da Meta em [muse.ai](https://muse.ai), nos workflows, chatflows e agentes do Dify. Gere vídeos de cerca de 10 segundos com som a partir de texto, dê vida a uma foto e faça a pessoa nela falar uma fala, edite um vídeo com pessoas das suas imagens, gere imagens a partir de texto ou de até 9 imagens de entrada e converse com o agente Muse, que pesquisa na web, escreve documentos e código e cria arquivos para você. Imagens, vídeos e documentos voltam como arquivos do Dify.

**Funciona na sua própria conta do Muse, e o plano gratuito serve.** Conecte várias contas do Muse e deixe o e-mail vazio: a useapi.net envia cada novo job a uma conta saudável, com cota restante e um slot de job livre, e a cota semanal de todas as contas se soma. Veja [Várias contas do Muse](#várias-contas-do-muse).

> Este plugin chama a [Muse API](https://useapi.net/docs/api-muse-v1?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin) da useapi.net, uma API de terceiros. Ela não é feita, afiliada nem endossada pela Meta. Você precisa de uma assinatura da useapi.net (US$ 15/mês, cobre todas as APIs da useapi.net) e de uma conta do Muse em muse.ai. O Muse está disponível nos EUA, Canadá, Japão, Singapura e Austrália (em 25 de novembro de 2026), então crie a conta em um deles; depois de adicionada, você pode chamar a API de qualquer lugar.

## Planos do Muse e cota semanal

O Muse mede o uso de cada conta por semana. Jobs e chats usam a cota da conta em que rodam; envios e downloads não usam.

| Plano do Muse | Preço | Cota semanal |
|---|---|---|
| Free | US$ 0 | não divulgada |
| Power | US$ 20/mês | 500 milhões de tokens do Muse |
| Maximum | US$ 100/mês | 3 bilhões de tokens do Muse |

Fonte: Meta, [About Muse subscriptions](https://www.meta.com/help/subscriptions/1021145227643680/), novembro de 2026, como listado na [configuração do Muse](https://useapi.net/docs/start-here/setup-muse#usage-limits) da useapi.net. A disponibilidade pode variar por região. Nos testes da useapi.net, no plano gratuito um vídeo usou de 2 a 3 por cento da cota semanal e uma imagem de 0 a 1 por cento; a Meta não divulga o custo por job. **Ver uso da conta do Muse** mostra quanto foi usado e quando renova. A tabela mostra só o plano do Muse. A assinatura da useapi.net (US$ 15/mês) é à parte.

## Início rápido

1. **Pegue um token de API da useapi.net.** Assine e copie o token: [Setup useapi.net](https://useapi.net/docs/start-here/setup-useapi?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin).
2. **Conecte uma conta do Muse.** Siga o [Setup Muse](https://useapi.net/docs/start-here/setup-muse?utm_source=marketplace.dify.ai&utm_medium=referral&utm_campaign=dify-plugin). A conta precisa de login com e-mail e senha, do cadastro concluído em muse.ai (incluindo a verificação de idade da Meta) e de uma imagem criada lá. Use a conta só para a API, sem outras ferramentas de automação.
3. **Instale e autorize o plugin e gere um vídeo.** Instale pelo [Dify Marketplace](https://marketplace.dify.ai/plugins/useapi/muse_useapi), ou envie o `.difypkg` das [releases no GitHub](https://github.com/useapi/muse-api/releases) em Plugins > Instalar plugin > Arquivo de pacote local. Em Ferramentas, abra "Meta Muse por useapi.net", clique em Autorizar, cole o token e salve. Depois adicione **Gerar vídeo** a um workflow com o prompt `A paper boat floating on a calm pond at sunrise, a frog on the bank says "Bon voyage!"`, proporção 16:9, e execute. O `.mp4` volta como arquivo.

| Credencial | Obrigatória | O que é |
|---|:-:|---|
| Token de API da useapi.net | Sim | O token do passo 1. O Dify o guarda como segredo. |
| E-mail padrão da conta do Muse | Não | Deixe vazio para a useapi.net escolher a conta. Preencha só para fixar todas as ferramentas em uma conta do Muse. |

Ao salvar as credenciais o plugin faz uma verificação, `GET /accounts`, que confirma que o token funciona e que há ao menos uma conta do Muse conectada. Ela não chama o Muse.

O plugin se conecta só a `https://api.useapi.net/v1/muse`, com o token no cabeçalho `Authorization: Bearer`. Os arquivos prontos são baixados da mesma API (`GET /assets/{assetId}`), que os transmite a partir da sua conta do Muse. Um Dify auto-hospedado precisa de HTTPS de saída para `api.useapi.net`. Não é preciso proxy, webhook nem conexão de entrada.

## Várias contas do Muse

Cada assinatura da useapi.net permite adicionar 3 contas do Muse, do mesmo jeito que a primeira ([Setup Muse](https://useapi.net/docs/start-here/setup-muse)). **Listar contas do Muse** mostra a saúde, o plano e o uso semanal de cada conta, e **Listar jobs em execução** mostra quantos slots de job cada uma usa.

**Como a conta é escolhida.** Com o e-mail vazio e um job sem arquivos de entrada, a useapi.net envia o job a uma conta saudável, com cota restante e um slot livre (`maxJobs`, 10 por padrão). Um job de vídeo também evita a conta que atingiu o limite de vídeos de 24 horas do Muse. Uma conta com a cota semanal esgotada fica de fora até renovar.

**As entradas fixam a conta.** Um arquivo enviado por você, ou feito pelo Muse, fica em uma conta do Muse, e todas as entradas de um job ou chat precisam estar na mesma conta. Por isso um pedido com IDs de entrada roda na conta deles, e os arquivos anexados são enviados para essa conta. Um chat continua na conta em que começou: siga com o `chat_id`.

## Ferramentas

13 ferramentas. Os IDs de ativos têm a forma `user:12345-email:<hex>-video:<nome>.mp4`; passe-os entre nós como variáveis.

| Ferramenta | Nome | Endpoint |
|---|---|---|
| `generate_image` | Gerar imagem | `POST /jobs/image` |
| `generate_video` | Gerar vídeo | `POST /jobs/video` |
| `get_job` | Ver status do job | `GET /jobs/{jobid}` |
| `list_jobs` | Listar jobs em execução | `GET /jobs` |
| `chat` | Chat com o Muse | `POST /chats`, `POST /chats/{chatId}/messages`, `GET /chats/{chatId}` |
| `get_chat` | Ver chat do Muse | `GET /chats/{chatId}` |
| `answer_approval` | Responder a um pedido de permissão do Muse | `POST /chats/{chatId}/approvals/{approvalId}` |
| `list_chats` | Listar chats do Muse | `GET /chats` |
| `upload_file` | Enviar arquivo ao Muse | `POST /assets` |
| `list_assets` | Listar a Biblioteca do Muse | `GET /assets` |
| `get_asset` | Baixar arquivo do Muse | `GET /assets/{assetId}` |
| `list_accounts` | Listar contas do Muse | `GET /accounts` |
| `get_account` | Ver uso da conta do Muse | `GET /accounts/{email}` |

O Muse é um agente, não um gerador fixo: não há ajustes de modelo, resolução ou duração. Descreva o que quer no prompt.

- **Gerar imagem**: uma imagem WebP de cerca de 2 a 2,5 megapixels. Com até 9 imagens de entrada (`image_1` a `image_9` no prompt), combine em uma cena, edite uma imagem ou restaure e colora uma foto antiga.
- **Gerar vídeo**: um MP4 de cerca de 10 segundos, cerca de 720p, com som. Texto para vídeo; imagem para vídeo, em que uma fala entre aspas é dita (uma foto falante); edição de vídeo. Entradas: até 9 imagens, 3 vídeos e 3 áudios, citados como `image_N`, `video_N`, `audio_N`.
- **Proporção.** A opção acrescenta `In exactly <proporção> aspect ratio` ao prompt, a forma que o Muse segue melhor.
- **Entradas.** Um ID de ativo ou um arquivo do Dify, que o plugin envia antes: imagens JPEG, PNG ou WebP, vídeos MP4, MOV ou WebM e áudios MP3, WAV, M4A ou OGG, até 50 MB cada.
- **Prompts repetidos.** O Muse lembra o que a conta já fez, entre chats. Mandar o mesmo prompt de novo na mesma conta pode ser recusado com `409`, sem gerar nada. Varie o prompt a cada nova imagem ou vídeo, ou use outra conta.

Saídas: texto legível (o que o agente lê), JSON, arquivos (acima de 150 MB não são anexados) e as variáveis `jobid`, `status`, `asset_ids`, `reply`, `chat_id` e `approval_ids`.

## Espera e limites

- **Limite de 600 segundos do Dify.** As ferramentas de geração enviam o job, consultam a cada 10 segundos e retornam depois de 120 segundos para imagens e 180 para vídeos, por padrão. Se o job não terminou, retornam o `jobid`: use **Ver status do job**. Em um workflow, a "Espera máxima" vai até 420 segundos. Os registros de jobs ficam 7 dias.
- **Tempo.** Nos testes da useapi.net uma imagem levou de 20 a 60 segundos e um vídeo de 60 a 140.
- **Slots de job.** Cada conta do Muse roda no máximo `maxJobs` jobs ao mesmo tempo (10 por padrão). Chats e envios não ocupam slot.
- **Limite de vídeos.** Além da cota semanal, o Muse limita os vídeos de uma conta nas últimas 24 horas. A conta então fica uma hora sem jobs de vídeo; jobs de imagem continuam.
- **Pedidos de permissão.** Antes de algumas ações, como compartilhar dados com um site, o agente pede permissão. O chat retorna `waiting_for_approval` com um `approval_id`: responda com **Responder a um pedido de permissão do Muse** antes de expirar.

## Solução de problemas

| Código | O que significa | O que fazer |
|---|---|---|
| 400 | O pedido está errado, por exemplo o prompt cita `image_2` sem uma segunda imagem, ou não há conta do Muse conectada. | Corrija o que a mensagem diz, ou conecte uma conta com o [Setup Muse](https://useapi.net/docs/start-here/setup-muse). |
| 401 | O token da useapi.net está errado. | Confira o token nas credenciais do plugin. |
| 402 | A assinatura da useapi.net não está ativa. | Renove: [subscription](https://useapi.net/docs/subscription). |
| 403 | O Muse se recusou a fazer (as palavras dele estão na mensagem), a Meta desligou o vídeo da conta na região dela, ou o ID é de outro token de API. Ou o Muse pediu permissão. | Mude o prompt ou as entradas: reenviar o mesmo não ajuda. Para vídeo, use outra conta. Se o Muse pediu permissão, execute como um chat do Muse e responda com `answer_approval`. |
| 404 | A conta não está conectada, ou o job, chat ou arquivo não existe mais. | Conecte a conta com o [Setup Muse](https://useapi.net/docs/start-here/setup-muse). |
| 409 | O Muse diz que a conta já fez esse pedido, então nada foi feito. Ou um pedido de permissão já foi respondido. | Mude o prompt, ou use outra conta. |
| 410 | O job expirou. | Os registros de jobs ficam 7 dias. |
| 412 | A cota semanal do Muse acabou na conta (ou em todas). | Espere a renovação (veja **Ver uso da conta do Muse**), ou conecte outra conta. |
| 429 | Todos os slots estão ocupados, o Muse está limitando a conta por um minuto, ou a conta atingiu o limite de vídeos de 24 horas. | Tente de novo após o horário da mensagem, ou deixe o e-mail vazio para outra conta assumir. |
| 502, 504 | O Muse respondeu com erro ou não terminou a tempo. O arquivo pode ter sido feito. | Confira **Ver status do job** ou **Listar chats do Muse** antes de rodar de novo. |
| 503 | Não foi possível falar com o Muse, ou ele falhou desta vez. | Rode de novo: o mesmo prompt costuma funcionar na próxima. |
| 596 | A conta precisa de atenção: a Meta pede uma verificação de segurança, ou o Muse recusou um novo login. Ou o Muse tirou o computador da conta. | Entre uma vez em muse.ai no navegador e adicione a conta de novo com o [Setup Muse](https://useapi.net/docs/start-here/setup-muse). Se o Muse tirou o computador da conta, peça ao suporte do Muse para restaurá-lo e depois adicione a conta de novo. |

## Custos

- O plugin é gratuito.
- useapi.net: US$ 15/mês, para todas as APIs da useapi.net.
- Meta: o seu plano do Muse, incluindo o gratuito. Jobs e chats usam a cota semanal dele.

## Privacidade

O plugin envia pedidos só para `api.useapi.net` e não guarda nada. Veja [PRIVACY.md](../PRIVACY.md) e os [Termos e Política de Privacidade](https://useapi.net/docs/legal) da useapi.net.

## Suporte

- Referência da API: https://useapi.net/docs/api-muse-v1
- Exemplos e o código do plugin: https://github.com/useapi/muse-api
- E-mail support@useapi.net, ou pergunte no [Discord](https://discord.gg/w28uK3cnmF) ou no [Telegram](https://t.me/use_api).
