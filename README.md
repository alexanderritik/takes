# Takes

**The review and history layer for AI video edits.** Your tool edits and
renders; Takes shows what changed and lets a person approve it.

- **Every edit is a request.** An agent's edit lands on a side line, not on
  the main timeline. A person reads exactly what changed, clip by clip, and
  approves it or not.
- **Many agents at once.** Edits made in parallel are combined clip by clip.
  When two touch the same thing, you get the conflict as data, never a
  silently broken timeline.
- **A full record.** Who changed which clip, when, and why; any version can
  be checked out again, and any change undone.

Takes is one binary. Your program calls it, sends timelines in as JSON,
reads JSON out, and branches on the exit code. It never copies or renders
your videos: they stay your tool's. AI agents can use it directly over MCP.

## Install

Linux and macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/alexanderritik/takes/main/install.sh | sh
```

Or download the latest build for your system and put `takes` on your `PATH`:

| System | Download |
|---|---|
| Linux, Intel/AMD (x86-64) | [takes_linux_amd64.tar.gz](https://github.com/alexanderritik/takes/releases/latest/download/takes_linux_amd64.tar.gz) |
| Linux, ARM (arm64) | [takes_linux_arm64.tar.gz](https://github.com/alexanderritik/takes/releases/latest/download/takes_linux_arm64.tar.gz) |
| macOS, Apple Silicon (M1 and later) | [takes_darwin_arm64.tar.gz](https://github.com/alexanderritik/takes/releases/latest/download/takes_darwin_arm64.tar.gz) |
| macOS, Intel | [takes_darwin_amd64.tar.gz](https://github.com/alexanderritik/takes/releases/latest/download/takes_darwin_amd64.tar.gz) |
| Windows, x86-64 | [takes_windows_amd64.zip](https://github.com/alexanderritik/takes/releases/latest/download/takes_windows_amd64.zip) |

Older versions are on [Releases](https://github.com/alexanderritik/takes/releases).
Each release has a `checksums.txt` (SHA-256) to check your download:

```bash
sha256sum -c checksums.txt --ignore-missing      # Linux
shasum -a 256 -c checksums.txt --ignore-missing  # macOS
```

**Requires ffmpeg** (Takes uses its `ffprobe`): `apt install ffmpeg`,
`brew install ffmpeg`, or `winget install Gyan.FFmpeg`.

**macOS:** the binary is not signed yet. If you downloaded it with a browser
and macOS refuses to open it, clear the download flag once:
`xattr -d com.apple.quarantine takes`. The install script does not need this.

**Windows:** SmartScreen may warn about an unknown publisher the first time;
choose *More info → Run anyway*.

## Quickstart

```bash
takes init -timeline timeline.json        # your editor's timeline becomes version 1
takes checkout > edit.json                # an agent edits it, then sends it back...
takes submit agent "tighten the intro" edit.json
takes review agent                        # ...and a person sees what changed
takes approve agent
```

No timeline yet? `takes init video.mp4` finds the shots in a video and starts
from those. `takes log`, `takes blame` and `takes revert` work on the record.

## With an AI agent

`takes mcp` serves the same commands as tools over the Model Context
Protocol. For example, with Claude Code:

```bash
claude mcp add takes -- takes -C /path/to/project mcp
```

The agent can check out, submit and read reviews. Approving stays with the
person: it is offered only with `takes mcp -owner`.

## Integrating

[CLI.md](CLI.md) is the contract: every command, its JSON, the exit codes,
and how conflicts are reported. Add `--json` to any command.

## Demo

[demo/](demo/) runs one real round trip on Linux or macOS: an agent edits an
MLT project (the format Shotcut and Kdenlive save) over MCP, a person
approves, and melt renders the result.

## Licence

Free to evaluate, including inside a company, and free for personal and
non-commercial use. Using Takes in a commercial product, service or
production work needs a licence: ask through
[issues](https://github.com/alexanderritik/takes/issues). See
[LICENSE](LICENSE).
