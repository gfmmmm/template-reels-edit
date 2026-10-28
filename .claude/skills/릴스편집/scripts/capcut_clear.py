#!/usr/bin/env python3
"""CapCut 프로젝트를 비운다 — 루트와, 한 번 연 프로젝트면 Timelines 사본(active timeline)까지.

사용법: capcut_clear.py <프로젝트> (CapCut이 꺼진 상태에서)
왜: 사용자가 한 번 연 프로젝트는 Timelines/<id>/draft_info.json 사본이 생기고, compile --into는 루트와 사본이
 둘 다 비어 있어야 한다("project must be empty in every root and active mirror"). 루트만 지우면 채우기가 실패한다(IMG_0519).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def segs(f):
    return [s["id"] for t in json.load(open(f))["tracks"] for s in t["segments"]] if os.path.exists(f) else []


def main(proj):
    if pu.capcut_running():
        sys.exit("CapCut이 켜져 있다. 꺼 달라고 요청하고 멈춘다.")
    root = os.path.join(proj, "draft_content.json")
    tl = os.path.join(proj, "Timelines")
    mirrors = [os.path.join(tl, d, "draft_info.json") for d in (os.listdir(tl) if os.path.isdir(tl) else [])]
    for _ in range(3):
        for i in segs(root):
            subprocess.run(["capcut", "remove", proj, i], capture_output=True)
        for m in mirrors:
            for i in segs(m):
                subprocess.run(["capcut", "remove", proj, i, "--active-timeline"], capture_output=True)
    left = len(segs(root)) + sum(len(segs(m)) for m in mirrors)
    print(json.dumps({"root": len(segs(root)), "mirrors": [len(segs(m)) for m in mirrors], "ok": left == 0}))
    sys.exit(0 if left == 0 else 1)


if __name__ == "__main__":
    main(sys.argv[1])
