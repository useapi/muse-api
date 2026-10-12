#!/usr/bin/env bash
# Everything in one command: start a Muse image job, wait for it, download the .webp. Prints the saved path.
# Usage: image.sh "<prompt>" [key=value ...]     (options as in generate.sh: image_1..image_9)
# Example: image.sh "In exactly 4:5 aspect ratio, the person from image_1 wearing the jacket from image_2." \
#            image_1=<assetId> image_2=<assetId>
# OUT_DIR sets the folder (default: the current one); the final job record is saved next to it as .json,
# with the new file's assetId in .result.assets[0].assetId for the next job.
# If the run is interrupted after "job ..." was logged, do NOT run it again (that uses the allowance twice). Resume with:
#   wait-job.sh <jobid> > job.json && download.sh job.json
DIR="$(dirname "$0")"
source "$DIR/_common.sh"
PROMPT="${1:?Usage: image.sh \"<prompt>\" [key=value ...]}"
shift

JOBID=$("$DIR/generate.sh" image "$PROMPT" ${1+"$@"})
JOB=$("$DIR/wait-job.sh" "$JOBID") || { echo "Not resubmitted. Job id: $JOBID" >&2; exit 1; }
FILE=$("$DIR/download.sh" - "${OUT_DIR:-.}" <<< "$JOB") || { echo "Resume the download with: download.sh <job.json> (job id $JOBID)" >&2; exit 1; }
echo "$JOB" > "${FILE%.*}.json"
log "assetId $(jq -r '.result.assets[0].assetId' <<< "$JOB")"
echo "$FILE"
