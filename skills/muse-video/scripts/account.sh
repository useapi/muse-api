#!/usr/bin/env bash
# Show the added Muse accounts, or read one account's plan and weekly allowance live from Muse.
# Usage: account.sh [email]     (default: USEAPI_EMAIL; with neither, lists every account as last read)
# quota.percentUsed is the share of the week used, in whole percent; quota.resetsAt is when it starts over.
# On the free plan a video uses about 2 to 3 percent and an image 0 to 1 percent.
# Docs: https://useapi.net/docs/api-muse-v1/get-muse-accounts-email
source "$(dirname "$0")/_common.sh"
EMAIL="${1:-${USEAPI_EMAIL:-}}"
if [ -n "$EMAIL" ]; then
  api_poll GET "accounts/$(enc "$EMAIL")" | jq '{email, health, maxJobs, session, quota: (.quota | {tier, percentUsed, resetsAt, quotaStatus})}'
else
  api_poll GET accounts | jq '[.[] | {email, health, maxJobs, quota: (.quota | {tier, percentUsed, resetsAt, quotaStatus})}]'
fi
