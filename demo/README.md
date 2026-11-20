# Demo: an agent edits an MLT project, a person approves, melt renders

One real round trip with a real editor's file format and renderer. MLT is
the engine under Shotcut and Kdenlive; `.mlt` is the project file they
save, and `melt` is its renderer.

Needs `takes` (see the main README), `python3`, `ffprobe` and `melt`, on
Linux or macOS:

```bash
sudo apt install melt ffmpeg python3     # Debian, Ubuntu
brew install mlt ffmpeg python           # macOS
demo/run.sh
```

`TAKES=/path/to/takes` and `MELT=/path/to/melt` pick binaries that are not
on your `PATH`.

What happens:

1. `project.mlt` is the Aladdin reel as an editor saved it: six shots of
   `media/aladdin.mp4` on one video track, at 30 fps. The script copies it
   and its media into `out/`, which plays the editor's project folder (takes
   reads only files inside the project folder). melt renders it to
   `out/before.mp4` (24 s).
2. `mlt.py to-takes` turns its track into a takes timeline (rate 30, frames,
   the videos referred to where they are, each shot's caption kept as a
   field takes does not read), and `takes init -timeline` makes it version 1.
3. `agent.py` starts `takes mcp` and, over MCP only, checks out main,
   tightens the opening by 1.5 s, swaps the carpet ending for the princess,
   renames the genie's caption, submits the edit request `agent`, and reads
   its review. It is not offered `approve`.
4. A person reads `takes review agent` (every change, the caption included)
   and approves it. Run from a terminal, the script asks first.
5. The approved timeline goes back into the project with `mlt.py from-takes`
   (`out/approved.mlt`, which Shotcut or Kdenlive can open), and melt renders
   it to `out/approved.mp4` (21.5 s).
6. `takes log` and `takes blame` show who changed what.

`mlt.py` is demo code, not part of takes: takes knows no editor and talks to
one only through the command line's JSON (`CLI.md`). It handles what this
project uses (tracks, entries, blanks, captions); a full converter would
also carry filters and transitions, as clip fields takes keeps as sent.

To have a real agent make the edit instead of `agent.py`, give it the MCP
server after step 2, for example with Claude Code:

```bash
claude mcp add takes -- takes -C "$PWD/demo/out" mcp
```
