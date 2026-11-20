#!/usr/bin/env python3
"""Convert between an MLT project (.mlt, what Shotcut and Kdenlive save and
melt renders) and a takes timeline. This is demo code, not part of takes:
takes knows no editor, and a tool talks to it only through the command
line's JSON (CLI.md).

  mlt.py to-takes   project.mlt              > timeline.json
  mlt.py from-takes project.mlt timeline.json > edited.mlt

What maps to what:

  profile frame_rate_num/den       -> rate
  each playlist in the tractor     -> a track (its shotcut:name, or its id)
  each entry in a playlist         -> a clip; in/out are frames, and MLT's out
                                      is the last frame shown, takes' the one after
  blank before an entry            -> the clip's start (takes stores it as a gap)
  the entry's producer resource    -> src, as the .mlt names it
  the entry's shotcut:caption      -> the clip field "caption", kept by takes as sent
  the entry's takes:id property    -> id, written back so it survives the round trip

from-takes keeps the .mlt's profile and anything it does not know, and
rebuilds the producers and playlists from the timeline.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET


def props(el):
    return {p.get("name"): (p.text or "") for p in el.findall("property")}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "clip"


def to_takes(path):
    root = ET.parse(path).getroot()
    profile = root.find("profile")
    num, den = profile.get("frame_rate_num"), profile.get("frame_rate_den", "1")
    producers = {p.get("id"): props(p) for p in root.iter("producer")}
    playlists = {p.get("id"): p for p in root.iter("playlist")}
    tractor = root.find("tractor")
    clips, used, layer = [], set(), 0
    for track in tractor.findall("track"):
        playlist = playlists[track.get("producer")]
        p = props(playlist)
        kind = "audio" if p.get("shotcut:audio") or track.get("hide") == "video" else "video"
        name = p.get("shotcut:name") or playlist.get("id")
        at = 0
        for item in playlist:
            if item.tag == "blank":
                at += int(item.get("length"))
            elif item.tag == "entry":
                first, last = int(item.get("in")), int(item.get("out"))
                ep = props(item)
                caption = ep.get("shotcut:caption", "")
                clip_id = ep.get("takes:id") or slug(caption)
                while clip_id in used:
                    clip_id += "-2"
                used.add(clip_id)
                clip = {"id": clip_id, "track": name, "kind": kind, "layer": layer,
                        "src": producers[item.get("producer")]["resource"],
                        "start": at, "in": first, "out": last + 1}
                if caption:
                    clip["caption"] = caption
                clips.append(clip)
                at += last + 1 - first
        if kind == "video":
            layer += 1
    rate = num if den == "1" else f"{num}/{den}"
    return {"rate": rate, "title": root.get("title", ""), "clips": clips}


def from_takes(path, timeline):
    tree = ET.parse(path)
    root = tree.getroot()
    num, den = (str(timeline["rate"]).split("/") + ["1"])[:2]
    profile = root.find("profile")
    if (profile.get("frame_rate_num"), profile.get("frame_rate_den", "1")) != (num, den):
        sys.exit("the timeline's rate is not the project's")
    for el in list(root):
        if el.tag in ("producer", "playlist", "tractor"):
            root.remove(el)
    if timeline.get("title"):
        root.set("title", timeline["title"])
    # Videos are named as the original project names them; MLT reads a
    # relative name from root, so the new file can be written anywhere.
    root.set("root", os.path.dirname(os.path.abspath(path)))

    # One producer per video, as long as the longest use of it.
    sources = {}
    for c in timeline["clips"]:
        sources[c["src"]] = max(sources.get(c["src"], 0), c["out"])
    ids = {}
    for i, (src, end) in enumerate(sources.items()):
        ids[src] = f"producer{i}"
        prod = ET.SubElement(root, "producer", id=ids[src], **{"in": "0", "out": str(end - 1)})
        ET.SubElement(prod, "property", name="resource").text = src
        ET.SubElement(prod, "property", name="mlt_service").text = "avformat"

    # One playlist per track, the clips in start order with blanks between.
    tracks = {}
    for c in timeline["clips"]:
        tracks.setdefault(c["track"], []).append(c)
    tractor_tracks = []
    for i, (name, clips) in enumerate(tracks.items()):
        playlist = ET.SubElement(root, "playlist", id=f"playlist{i}")
        audio = clips[0]["kind"] == "audio"
        ET.SubElement(playlist, "property", name="shotcut:audio" if audio else "shotcut:video").text = "1"
        ET.SubElement(playlist, "property", name="shotcut:name").text = name
        at = 0
        for c in sorted(clips, key=lambda c: c["start"]):
            if c["start"] > at:
                ET.SubElement(playlist, "blank", length=str(c["start"] - at))
            entry = ET.SubElement(playlist, "entry", producer=ids[c["src"]],
                                  **{"in": str(c["in"]), "out": str(c["out"] - 1)})
            ET.SubElement(entry, "property", name="takes:id").text = c["id"]
            if c.get("caption"):
                ET.SubElement(entry, "property", name="shotcut:caption").text = c["caption"]
            at = c["start"] + c["out"] - c["in"]
        tractor_tracks.append((playlist.get("id"), audio))
    tractor = ET.SubElement(root, "tractor", id="tractor0")
    for pid, audio in tractor_tracks:
        attrs = {"producer": pid}
        if audio:
            attrs["hide"] = "video"
        ET.SubElement(tractor, "track", **attrs)
    root.set("producer", "tractor0")
    ET.indent(tree)
    tree.write(sys.stdout.buffer, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "to-takes":
        json.dump(to_takes(sys.argv[2]), sys.stdout, indent=2)
    elif len(sys.argv) == 4 and sys.argv[1] == "from-takes":
        with open(sys.argv[3]) as f:
            from_takes(sys.argv[2], json.load(f))
    else:
        sys.exit(__doc__)
