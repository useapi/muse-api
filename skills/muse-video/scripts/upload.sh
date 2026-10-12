#!/usr/bin/env bash
# Upload a local image, video or audio file to a Muse account and print its assetId.
# Usage: upload.sh <file>
# The file goes into the Muse workspace of the account (USEAPI_EMAIL, or a healthy account picked by the API);
# nothing is stored at useapi.net. Uploads are free (no Muse allowance) and idempotent: the same file on the
# same account always gets the same assetId, so this is safe to run again.
# Formats: jpeg, png, webp, mp4, mov, webm, mp3, wav, m4a, ogg. At most 52,428,800 bytes (50 MB).
# All inputs of one job must be on the same account, so set USEAPI_EMAIL when the user has several.
# Docs: https://useapi.net/docs/api-muse-v1/post-muse-assets
source "$(dirname "$0")/_common.sh"
FILE="${1:?Usage: upload.sh <file>}"
[ -f "$FILE" ] || { echo "No such file: $FILE" >&2; exit 1; }
SIZE=$(wc -c < "$FILE" | tr -d ' ')
[ "$SIZE" -le 52428800 ] || { echo "$FILE is $SIZE bytes; Muse uploads take at most 52,428,800 bytes (50 MB). Make it smaller first." >&2; exit 1; }

# The MIME type from the file's content when `file` is available (a .jpeg can really be a WebP), else from the extension
MIME=""
if command -v file > /dev/null; then MIME=$(file --mime-type -b "$FILE" 2>/dev/null || true); fi
case "$MIME" in
  image/jpeg|image/png|image/webp|video/mp4|video/quicktime|video/webm|audio/mpeg|audio/wav|audio/x-wav|audio/mp4|audio/x-m4a|audio/ogg) ;;
  *)
    EXT=$(printf '%s' "${FILE##*.}" | tr 'A-Z' 'a-z')
    case "$EXT" in
      jpg|jpeg) MIME=image/jpeg ;; png) MIME=image/png ;; webp) MIME=image/webp ;;
      mp4) MIME=video/mp4 ;; mov) MIME=video/quicktime ;; webm) MIME=video/webm ;;
      mp3) MIME=audio/mpeg ;; wav) MIME=audio/wav ;; m4a) MIME=audio/mp4 ;; ogg) MIME=audio/ogg ;;
      *) echo "Unsupported file type: $FILE (use jpeg, png, webp, mp4, mov, webm, mp3, wav, m4a or ogg)" >&2; exit 1 ;;
    esac ;;
esac

P=assets
if [ -n "${USEAPI_EMAIL:-}" ]; then P="assets?email=$(enc "$USEAPI_EMAIL")"; fi
# An upload is free and idempotent, so a network error, 502 or 503 is retried (3 tries, 10 s apart)
for TRY in 1 2 3; do
  OUT=$(mktemp)
  CODE=$(acurl -sS --max-time 600 -o "$OUT" -w '%{http_code}' -X POST "$API/$P" -H "Content-Type: $MIME" --data-binary @"$FILE") || true
  CODE="${CODE:-000}"
  case "$CODE" in
    000|502|503) if [ "$TRY" -lt 3 ]; then log "POST /assets -> HTTP $CODE, retry $TRY of 2 in 10 s"; rm -f "$OUT"; sleep 10; continue; fi ;;
  esac
  break
done
R=$(_finish POST assets)
log "uploaded $(jq -r '"\(.type) (\(.mime), \(.bytes) bytes) to \(.email)"' <<< "$R")"
jq -r .assetId <<< "$R"
