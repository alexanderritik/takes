#!/usr/bin/env bash
# One real round trip: an AI agent edits an MLT project (what Shotcut and
# Kdenlive save) through takes over MCP, a person approves it, and MLT's own
# renderer, melt, renders the result. See README.md.
#
# Needs: takes, python3, ffprobe, and melt (apt install melt / brew install
# mlt). TAKES=/path/to/takes and MELT=/path/to/melt pick other ones. Run it
# from anywhere; it works in demo/out/, which it makes afresh each time.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bin="${TAKES:-takes}"
melt="${MELT:-melt}"
for need in "$bin" "$melt" python3 ffprobe; do
  if ! command -v "$need" >/dev/null; then
    echo "$need is not installed; see demo/README.md" >&2
    exit 1
  fi
done
bin="$(command -v "$bin")"
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

# out/ is the editor's project folder: the project file and its media. Takes
# reads only files inside it, and copies none of them.
out="$here/out"
rm -rf "$out"
mkdir -p "$out/media"
cp "$here/project.mlt" "$out/"
cp "$here/media/aladdin.mp4" "$here/media/princess.mp4" "$out/media/"
takes() { "$bin" -C "$out" "$@"; }

say "1. The editor's project, rendered by melt as it is now."
"$melt" -quiet "$out/project.mlt" -consumer "avformat:$out/before.mp4" >/dev/null 2>&1
echo "  $out/before.mp4: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out/before.mp4")s"

say "2. Its timeline becomes version 1 in takes. The videos stay where they are."
python3 "$here/mlt.py" to-takes "$out/project.mlt" > "$out/timeline.json"
takes init -timeline timeline.json

say "3. An agent edits it through MCP and sends an edit request."
python3 "$here/agent.py" "$bin" "$out"

say "4. A person reviews what the agent changed."
takes review agent
if [ -t 0 ]; then
  read -r -p "Approve it? [y/N] " answer
  [ "$answer" = y ] || { echo "Not approved; main is unchanged."; exit 0; }
else
  echo "(not a terminal: approving, as the person running the demo)"
fi
takes approve agent

say "5. The approved timeline goes back into the project, and melt renders it."
takes checkout > "$out/main.json"
python3 "$here/mlt.py" from-takes "$out/project.mlt" "$out/main.json" > "$out/approved.mlt"
"$melt" -quiet "$out/approved.mlt" -consumer "avformat:$out/approved.mp4" >/dev/null 2>&1
echo "  $out/approved.mlt  (open it in Shotcut or Kdenlive)"
echo "  $out/approved.mp4: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out/approved.mp4")s"

say "6. The record: who changed what, and when."
takes log
takes blame
