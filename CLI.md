# The takes command line

This is the contract between Takes and the programs that use it: video
editors, AI agents, scripts. Your program calls the `takes` binary, sends
timelines in as JSON, reads JSON out, and branches on the exit code. There
is no library to link and no server to run.

JSON format: **2**. `takes version --json` says which format a binary speaks.
Every time is a whole number of **frames** at the project's rate.

## The loop in one minute

```bash
# Your editor's timeline becomes version 1 on main.
takes init -timeline timeline.json --json

# Each agent (or person) gets the timeline to edit...
takes checkout --json > agent-a.json
#   ...edits it however it likes, then sends it back as an edit request.
takes submit agent-a "tighten the intro" agent-a.json --json

# The owner looks before combining: review is a dry run of approve.
takes review agent-a --json
takes approve agent-a --json      # exit 4 if it conflicts; main is then unchanged
```

Every command is run inside the project folder, or pointed at it with
`-C dir`. Takes keeps its records in `.takes/` there. It does not copy or
keep videos: a clip names its video, and the video stays the tool's.

An AI agent can use the same commands as tools over MCP: see `mcp` below.

## Calling conventions

| Rule | Detail |
|---|---|
| `--json` | Anywhere on the line before a `--`. stdout is then exactly one JSON document, on success **and** on failure. Nothing is printed on stderr. |
| Without `--json` | Output is for people and may change between releases. Do not parse it. The one exception is `checkout`, which always prints its snapshot as JSON. |
| Exit code | Always set; see the table below. With `--json` the error document says the same thing in more detail. |
| `-C dir` | The project folder. Defaults to the current folder. Goes before the command. Like `git -C`, takes runs as if started there: a file argument (`init -timeline t.json`, `submit kim x t.json`) is found from it. |
| stdin | Read only by `submit` (when the file is `-` or left out) and `init -timeline -`. No command ever prompts. If stdin is a terminal, they refuse rather than wait. |
| `--` | Everything after it is an argument, even if it starts with `-`. |
| Help | `takes help`, `takes help <command>`, `takes <command> --help`. `takes --json help` lists the commands as data. |
| Version | `takes --version`, or `takes version --json` for `{"version", "format"}`. |

A command that takes no flags refuses anything else that starts with `-`
(exit 2), so a typo never turns into a cut name.

## Exit codes

| Exit | Meaning | Error codes |
|---|---|---|
| 0 | done | |
| 1 | failed for a reason not below | `failed` (a bug, a disk error), `busy` (another command held the project for 30 seconds; try again), `damaged` (the project's files are missing or altered; run `check`) |
| 2 | called wrongly | `usage` |
| 3 | something named does not exist | `not_a_project`, `not_found` |
| 4 | merge conflict; nothing was changed | `conflict` |
| 5 | refused; nothing was changed | `invalid`, `no_change`, `already_exists`, `old_format` (the project was made by a takes that wrote another format) |
| 6 | the edit started from an old version; check out again and redo it | `stale_base` |

Exit codes are coarse, error codes are fine-grained. Branch on the exit code
and log the error code. A code is never renamed or reused; new ones may be
added within an exit code.

## Errors

```json
{
  "error": {
    "code": "conflict",
    "message": "lee conflicts with main; main is unchanged",
    "conflicts": [ ... ]
  }
}
```

`message` is a sentence for a person and may change. `conflicts` is there
only when `code` is `conflict`, and `problems` only when `check` found
some (see `check`).

## The timeline (snapshot)

`checkout` prints a snapshot, and `submit` and `init -timeline` read one.
Clips are listed in playing order. Clips on different tracks may be
interleaved in the list; order matters only within a track.

```json
{
  "base": "<the version this edit started from>",
  "rate": "25",
  "clips": [
    { "id": "a", "track": "main", "kind": "video", "layer": 0,
      "src": "media/interview.mp4", "start": 0, "in": 0, "out": 75 },
    { "id": "m", "track": "music", "kind": "audio", "layer": 0,
      "src": "asset:8812", "media": "sha1:9f2c…", "duration": 4500,
      "start": 50, "in": 0, "out": 300 }
  ]
}
```

| Field | Meaning |
|---|---|
| `base` | The version you checked out. Send it back unchanged. `init` ignores it. |
| `rate` | The project's frame rate: `"25"`, or a fraction such as `"30000/1001"` for 29.97 (a number such as `25` is taken too). Between 1 and 1000 frames a second, with a denominator of at most 1,000,000. Required by `init -timeline`; it never changes after. On submit it may be left out; if given it must be the project's. |
| `id` | The clip's identity across versions. **Keep it** for every clip you did not delete. A new clip needs a new ID, unique in the timeline. |
| `track` | The row the clip is on. Default `main`. |
| `kind` | `video` or `audio`. Left out, a clip keeps the kind it had; a new clip whose `src` Takes can open is `audio` if the file holds only sound, otherwise `video`. A new clip whose `src` it cannot open must say its kind. |
| `layer` | Stacking order for overlays; higher is on top. |
| `src` | Your name for the video: your media ID, a URL, or the path of a file inside the project folder, from it (`media/a.mp4`). Kept exactly as sent. An absolute path, a path that leads out with `..`, a link that leads out, or a path into `.takes` is refused. |
| `media` | Optional: your fingerprint or version of the video. Kept as sent; a change shows as the video being replaced. |
| `duration` | Optional: the video's length in frames, for videos Takes cannot open. Clips of one video must give the same duration. |
| `start` | The clip's first frame on the timeline. Checkout always gives it. |
| `in`, `out` | The clip's first frame in its video, and the frame after its last. |
| `volume` | Optional multiplier; absent or 0 means full volume. |
| `muted` | Optional. |

**Videos are referred to, not copied.** Takes opens only files inside the
project folder: a timeline cannot make it read, or the review server send,
any other file on the machine. When `src` is such a file, Takes asks ffprobe
for its length and whether it has pictures, to check `out` and to tell video
from audio, and records a fingerprint of the file (its size and a hash of
its start, middle and end). If the file is later swapped for another under
the same name, the next submit shows `clip a video a.mp4 was replaced on
disk by a different file`, and `check` reports it. A URL or a media ID it
cannot open; it then checks `out` against `duration` if you give one, and
trusts it if not, and you send `media` if you want a replacement noticed. A
`src` that reads like a file name but is not there is refused as a likely
typo, unless the clip says its kind. Old versions refer to videos you may
since have deleted: keeping them is the tool's job.

**Start times.** Agents, note: trimming a clip no longer moves the clips
after it. If a track's clips have `start`, they play in that order,
and every clip of the track must have one; two clips on a track may not
overlap. A clip that keeps its `start` stays where it is: trim the clip
before it and a gap opens. To close it up (a ripple edit), move the later
clips' starts, or leave `start` out on every clip of the track: the clips
then play in the order listed, each keeping the gap it had before it.
Either way Takes stores the space before each clip, not its start, so a
ripple edit is one change to the clip you trimmed, not a change to every
clip after it.

**Every other field is kept.** A clip may carry any other fields (`color`,
`transition`, an effect's settings), and the timeline any other top-level
fields (`size`, `name`, ...). Takes keeps them exactly as sent, values and
all, and gives them back on checkout, beside its own fields. Changing one is
a change: it shows in review (`clip a color "red" -> "blue"`,
`project size set to {"w":1920,"h":1080}`). They are merged one field at a
time, and fields inside an object one by one, all the way down: two agents
setting `fx.a` and `fx.b` are both kept. Takes never reads what they mean.

**Field names and case.** Takes' own field names are lowercase, and a field
that is one of them in other letters (`ID`, `Rate`) is refused, not guessed
at: it would otherwise be read as Takes' field and kept as yours. Any other
field is yours, and its name is kept exactly, as JSON names are: `color` and
`Color` are two fields, and both come back.

What makes merges come out right:

- **Splitting a clip:** keep the old ID on the first part and give the other
  parts new IDs. Two agents can then cut different parts of one long clip and
  both edits are kept.
- **Renamed clips are recognised.** If your editor gives a clip a new ID when
  its in point is trimmed, Takes sees that a clip's ID is gone and that a new
  clip plays part of the same stretch of the same video on the same track. It
  gives that clip its old ID back on submit, so you don't need to work around
  it. Because that changes what you sent, it is shown as a change of its own:
  `clip b came back as b2 and was kept as b: it plays part of the same footage`.

## Conflicts

A conflict is one thing that both sides changed and that cannot be kept
both ways. **Ours** is main; **theirs** is the edit request.

```json
{
  "kind": "property",
  "clip": "a",
  "property": "in",
  "base": 0,
  "ours": 25,
  "theirs": 50,
  "message": "clip a: in point changed to 25 and 50"
}
```

| `kind` | What collided | Fields |
|---|---|---|
| `property` | both changed one property of a clip differently | `property` is one of `src`, `media`, `file`, `duration`, `in`, `out`, `track`, `layer`, `volume`, `gap`, `position`. `base`, `ours` and `theirs` are its three values. `gap` is the frames of space before the clip on its track; `file` is Takes' fingerprint of a video in the project folder, when the two sides saw different files under one name. `position` (the clip's place in the order) has no values. |
| `delete_edit` | one side deleted the clip, the other edited it | `ours` and `theirs` are `"deleted"` or `"edited"` |
| `both_added` | both added a clip with this ID, differently | |
| `same_range` | both changed the same frames of a clip that was cut into parts | `ours`, `theirs`: frame ranges `[in, out]` |
| `same_place` | both put clips in the same place | `clip` is the clip they went after or inside (`""` for the start of a track); `ours`, `theirs` are the clips each side put there |
| `attribute` | both changed one of a clip's other fields differently | `property` is the field's path (`color`, or `fx.a` inside an object); `base`, `ours`, `theirs` its values as sent, left out where that side has no such field |
| `setting` | both changed one of the timeline's other top-level fields differently | `clip` is `""`; `property`, `base`, `ours`, `theirs` as for `attribute` |
| `no_history` | the two cuts share no history | `clip` is `""` |

Takes never resolves a conflict itself. To fix one, check out main as it
is now, redo the edit on top of it, and submit it to the same cut. That
submit is accepted even though the cut is elsewhere, because main has moved
on past the request; the request then holds everything on main and can be
approved. A request that has fallen behind main without a conflict is
brought up to date with `update`.

## Commands

Every result below is what `--json` prints. Versions are full 64-character
hashes, times are frames, and timestamps are RFC 3339. Lists are `[]`, never
`null`. Fields may be added to any object; none are removed or renamed.

`changes.lines` describe every difference between two versions: a clip
added, removed, cut into parts, or moved; its video, media, duration, in
point, out point, track, kind, layer, volume, mute, the space before it, or
any of its other fields changed; a top-level field of the timeline changed;
or a clip recognised under a new ID. Nothing that differs is left out. A
long value is shortened in the sentence (it stays whole in a conflict's
`base`, `ours` and `theirs`). The sentences are for people and may change;
`changed` and `total` count clips.

### init

```
takes init -timeline <file|->                            import a timeline as version 1
takes init [-rate r] [-scene n] [-min s] <video> [names...]   find the shots in a video
```

Returns the timeline of main:

```json
{ "cut": "main", "version": "…", "rate": "25", "clips": [ …snapshot clips… ],
  "tracks": ["main"], "length": 150 }
```

`length` is in frames. `settings` is added, as an object, when the timeline
has other top-level fields.

`init -timeline` needs `rate`. `init <video>` takes the video's frame rate
unless `-rate` gives another, and refers to the video by the path given; a
video of sound only has no frame rate, so it needs `-rate`, and becomes one
audio clip of the whole file.

Refuses with `already_exists` (exit 5) if the folder is already a project.
An init that is refused leaves the folder as it was.

### checkout

`takes checkout [cut]` (default `main`) returns the snapshot to edit.

### submit

`takes submit <cut> <title> [file|-]` sends an edited snapshot back as the
edit request for `<cut>`, which is usually the agent's or person's own name.
It reads stdin when the file is `-` or left out.

```json
{ "cut": "kim", "version": "…", "base": "…", "title": "trim a",
  "changes": { "changed": 1, "total": 2, "lines": ["clip a in point 0 -> 25"] } }
```

Submitting again to the same cut updates its request. It must start from
that cut's latest version, from a version that already contains it (for
example, main after the request was approved), or from main as it is now
when main has moved on past the request (how a conflict is fixed, see
Conflicts); otherwise `stale_base` (exit 6). It is refused with `invalid`
(exit 5) for broken JSON, a field of the wrong type (such as a time that is
not a whole number), an empty title, a rate that is not the project's, a
clip outside its video, a new clip whose kind cannot be told, overlapping
clips, duplicate IDs, the cut name `main`, or a name that differs from an
existing cut's only in case (`Kim` next to `kim`), and with `no_change`
(exit 5) if nothing changed. A refused submit stores nothing.

### requests

```json
{ "requests": [
  { "cut": "kim", "title": "trim a", "status": "open", "version": "…",
    "can_merge": true, "conflicts": [] } ] }
```

`status` is `open`, `merged` or `closed`. `can_merge` and `conflicts` are
against main as it is now.

### review

`takes review <cut>` is a dry run of approve. A conflict is part of the
answer, not a failure: it exits 0 with `can_merge: false`.

```json
{ "cut": "lee", "title": "trim a more", "status": "open", "version": "…",
  "can_merge": false, "conflicts": [ … ],
  "base": "…", "main": "…",
  "changes": { "changed": 1, "total": 2, "lines": ["clip a in point 0 -> 50"] },
  "length_now": 125, "length_if_approved": null }
```

`base` is the common ancestor of main and the request, and `changes` is what
the request changed since then. Lengths are frames; `length_if_approved` is
`null` when it cannot be approved.

### approve

`takes approve <cut>` combines an open request into main.

```json
{ "cut": "kim", "version": "…", "base": "…", "merged": false }
```

`version` is what main points at now. `merged` is false when main had not
moved, so it simply moved forward to the request. With a conflict it fails
with exit 4 and `code: conflict`, and main is unchanged. A request that was
already approved or closed is `not_found` (exit 3), and the message says
which.

### update

`takes update <cut>` brings an open request up to date with main: what main
gained since the request began is combined into the cut, as a new version on
it.

```json
{ "cut": "sam", "version": "…", "base": "…", "merged": true }
```

`version` is what the cut points at now and `base` the common ancestor.
With a conflict it fails with exit 4 and `code: conflict`, and the request
is unchanged; fix it as Conflicts describes. `no_change` (exit 5) if the
request already has everything on main.

### close

`takes close <cut>` drops an open request without combining it. Its
versions stay in the history, and submitting to the cut again opens it
again. `not_found` (exit 3) if the cut has no open request.

```json
{ "cut": "sam", "status": "closed" }
```

### revert

`takes revert <version> [message]` takes main back to an earlier version's
timeline, recorded as a **new** version (like `git revert`; nothing is
erased). `<version>` may be a unique prefix from `log`.

```json
{ "cut": "main", "version": "…", "reverts_to": "…", "message": "back to the import",
  "changes": { "changed": 1, "total": 2, "lines": ["clip a in point 25 -> 0"] } }
```

### log

```json
{ "versions": [
  { "hash": "…", "parents": ["…"], "author": "kim", "message": "trim a",
    "time": "2026-11-20T10:00:00.123456789+05:30", "cuts": ["kim", "main"] } ] }
```

Newest first. `cuts` are the cuts pointing at that version.

### show, diff

`takes show [cut]` returns a timeline, in the same shape as `init`.

`takes diff <cut> <cut>`:

```json
{ "from": { "cut": "main", "version": "…" }, "to": { "cut": "lee", "version": "…" },
  "changes": { "changed": 1, "total": 2, "lines": ["clip a in point 25 -> 50"] } }
```

### blame, history

`takes blame [cut]` says who last changed each clip:

```json
{ "cut": "main", "version": "…", "clips": [
  { "clip": "a", "track": "main", "in": 25, "out": 75,
    "version": "…", "author": "kim", "message": "trim a", "time": "…" } ] }
```

`takes history <clip|frame> [cut]` is every change to one clip, newest
first. Given a number, it is the clip playing at that frame of the cut (on
the main track, or the first track if there is none called main), and `at`
says where, with `source` the frame of the clip's video on screen then:

```json
{ "cut": "main", "clip": "a", "at": { "frame": 37, "source": 62 },
  "changes": [
    { "version": "…", "author": "kim", "message": "trim a", "time": "…",
      "what": ["clip a in point 0 -> 25"] } ] }
```

`via` is added to a change made on another cut: the version that brought it
into this one. A clip that was removed still has a history: its newest
change is the removal.

### check

`takes check` reads every stored record and checks it against its hash, and
checks that every cut, request and version finds what it points at. It also
checks each video in the project folder that a cut plays against the
fingerprint recorded for it, and reports one that is gone or was replaced by
a different file. It changes nothing. Videos it cannot open (URLs, media
IDs) are not looked at.

```json
{ "ok": true, "objects": 17, "problems": [] }
```

If anything is wrong it fails with exit 1 and `code: damaged`, and the
error lists each problem:

```json
{ "error": { "code": "damaged", "message": "found 1 problem(s) in 17 objects",
  "problems": [ { "file": "media/a.mp4", "message": "has been replaced by a different file since main recorded it (clip a); main no longer plays as recorded" } ] } }
```

`file` is the record (from `.takes`, such as `objects/…`) or the video (as
clips name it) that is wrong.

Every command also checks each stored record it reads, and fails with
`damaged` rather than use one that does not match its hash.

### mcp

`takes mcp [-owner]` serves the commands as tools to an AI agent over the
Model Context Protocol, on stdin and stdout, until stdin closes. Register it
with an agent as the command `takes -C <project> mcp`.

Each tool runs the command of the same name with `--json` and answers with
the document that command prints, as text and as `structuredContent`;
`isError` is true when the command failed. The tools are `checkout`,
`submit` (arguments `cut`, `title`, and `timeline`, the object checkout
returned), `requests`, `review`, `update`, `show`, `diff`, `history` and
`log`. `approve` and `close` are the owner's decisions and are offered
only with `-owner`: Takes cannot yet tell an agent from the owner, so an
agent given `-owner` can approve its own edits.

### version, serve

`takes version` returns `{ "version": "1.0.0", "format": 2 }`.

`takes serve [-addr host:port]` runs the review pages and an HTTP API until
stopped. It prints no JSON (with `--json` it exits 2). It answers only
requests addressed to localhost, a loopback address or the host in
`-addr` (any of this machine's addresses when `-addr` is `0.0.0.0:port`),
and refuses requests a browser sends from another site's pages, so a web
page cannot reach it. The pages play a video only if a cut plays it and it
is a file inside the project folder.

## The HTTP API

`serve` offers the same operations over HTTP under `/takes/api/`, with the
same JSON shapes for timelines, conflicts and errors. A request that changes
something must be a `POST` carrying an `X-Takes` header (any value). Errors
use the same `{"error": {...}}` document, with these statuses:

| Status | Error codes |
|---|---|
| 400 | `invalid` |
| 403 | `forbidden` (missing `X-Takes` header, another host name, or another site's page) |
| 404 | `not_found` |
| 409 | `conflict`, `no_change`, `already_exists`, `stale_base`, `old_format` |
| 500 | `failed`, `damaged` |
| 503 | `busy` |

The command line is the primary contract. The HTTP routes are for the
review pages, and are documented here only for their errors.

## Stability

- Format 2 only ever grows: new commands, new fields, new error codes. If a
  shape ever has to break, `format` goes up and the change is listed here.
- Every shape on this page is frozen by tests.
  A change to the output fails the build until the golden files are
  deliberately updated.
- The human output and the `message` sentences are not part of the contract.

### Format 2 (from format 1)

- Times are whole frames at the project's `rate`, not seconds: `in`, `out`,
  `length`, `length_now`, `length_if_approved`, blame's `in` and `out`,
  conflict values and ranges. `history` takes a frame, and `at` is
  `{frame, source}`.
- The snapshot and timeline carry `rate`; clips carry `start`, and may carry
  `duration`. `gap` is no longer a snapshot field: send `start`.
- `src` is your reference to the video and is kept as sent; `media` is your
  optional fingerprint. A path must be inside the project folder. Takes no
  longer copies videos into `.takes`, so `check` has no `media` count; it
  checks local videos against fingerprints instead.
- A project made by a format 1 takes is refused with `old_format` (exit 5).
  Start a new project from your editor's timeline.
