#!/usr/bin/env python3
"""A stand-in for an AI agent editing the reel. It reaches takes only over
MCP, the way an agent such as Claude would: it starts `takes mcp`, checks
out main, edits the timeline, submits its edit request, and reads the review
back. It cannot approve: that is the owner's decision, and `takes mcp`
without -owner does not offer it.

A real agent decides the edit itself. This one makes a fixed edit, in
seconds as a person thinks of them:

  - tighten the opening: start the market 1.5 s later
  - end on the princess: drop the carpet, add the princess after the palace
  - rename the genie shot's caption (a field takes keeps but does not read)

Usage:  agent.py <takes binary> <project folder>
"""
import json
import subprocess
import sys

takes, project = sys.argv[1], sys.argv[2]
server = subprocess.Popen([takes, "-C", project, "mcp"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, text=True)
next_id = 0


def call(method, params=None):
    global next_id
    next_id += 1
    server.stdin.write(json.dumps({"jsonrpc": "2.0", "id": next_id, "method": method, "params": params or {}}) + "\n")
    server.stdin.flush()
    answer = json.loads(server.stdout.readline())
    if "error" in answer:
        sys.exit(f"agent: {method} failed: {answer['error']['message']}")
    return answer["result"]


def tool(name, **arguments):
    result = call("tools/call", {"name": name, "arguments": arguments})
    doc = result["structuredContent"]
    if result["isError"]:
        sys.exit(f"agent: {name} refused: {doc['error']['code']}: {doc['error']['message']}")
    return doc


info = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "demo-agent", "version": "1"}})
server.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
tools = [t["name"] for t in call("tools/list")["tools"]]
print(f"agent: connected to {info['serverInfo']['name']} {info['serverInfo']['version']}; tools: {', '.join(tools)}")

timeline = tool("checkout")
num, _, den = timeline["rate"].partition("/")
fps = int(num) / int(den or 1)
frames = lambda seconds: round(seconds * fps)
clips = timeline["clips"]
by_id = {c["id"]: c for c in clips}

# This agent edits like an editor that ripples: it leaves start times out,
# so the clips after an edit close up behind it.
for c in clips:
    c.pop("start", None)
by_id["the-market"]["in"] += frames(1.5)
by_id["the-genie"]["caption"] = "The genie appears"
clips.remove(by_id["the-carpet"])
palace = clips.index(by_id["the-palace"])
clips.insert(palace + 1, {"id": "the-princess", "track": "V1", "kind": "video", "layer": 0,
                          "src": "media/princess.mp4",
                          "in": 0, "out": frames(3), "caption": "The princess"})

sent = tool("submit", cut="agent", title="tighten the opening, end on the princess", timeline=timeline)
print(f"agent: submitted edit request 'agent' ({sent['changes']['changed']} clips changed)")
review = tool("review", cut="agent")
print("agent: the review says it", "can be approved" if review["can_merge"] else "conflicts with main")
server.stdin.close()
server.wait()
