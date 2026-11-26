"""Tool -> API endpoint (catalog operation id), for the README tables and the routing check."""

ENDPOINTS = {
    "list_accounts": ("GET /accounts", "accounts-list"),
    "get_account": ("GET /accounts/{email}", "accounts-get"),
    "list_jobs": ("GET /jobs", "jobs-list"),
    "get_job": ("GET /jobs/{jobid}", "jobs-get"),
    "generate_image": ("POST /jobs/image", "jobs-image"),
    "generate_video": ("POST /jobs/video", "jobs-video"),
    "upload_file": ("POST /assets", "assets-upload"),
    "list_assets": ("GET /assets", "assets-list"),
    "get_asset": ("GET /assets/{assetId}", "assets-get"),
    "chat": ("POST /chats, POST /chats/{chatId}/messages, then GET /chats/{chatId}", "chats, chats-messages, chats-get"),
    "get_chat": ("GET /chats/{chatId}", "chats-get"),
    "answer_approval": ("POST /chats/{chatId}/approvals/{approvalId}, then GET /chats/{chatId}", "chats-approvals-update, chats-get"),
    "list_chats": ("GET /chats", "chats-list"),
}
