#!/usr/bin/env python3
"""3단계 ③-E-1 CapCut 프로젝트 글자 점검·수리 — CapCut이 실제로 그릴 때 깨지는 함정을 파일에서 바로잡는다.

사용법: capcut_textfix.py <CapCut 프로젝트> [--check]
- text-ranges가 지운 글꼴·외곽선·그림자: 범위 스타일마다 같은 프로젝트의 정상 자막 스타일(글꼴·외곽선·그림자)을 다시 입힌다. 범위·색·크기는 그대로.
- 상단 제목(외곽선·그림자 없음, 글꼴 id 빈칸): 제목 프리셋 값으로 외곽선·그림자·글꼴 id를 넣는다.
- 자막 줄 폭(line_max_width) 1.0 미만 → 1.0 (0.82에서 9~10자가 두 줄로 꺾였다).
- 루트 draft_info.json·draft_content.json·template-2.tmp와 Timelines/*/ 사본을 모두 같은 내용으로 고친다. CapCut이 켜져 있으면 멈춘다.
--check: 고치지 않고 문제 개수만 보고(종료 코드 1 = 문제 있음).
"""
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def files(proj):
    out = [os.path.join(proj, f) for f in ("draft_info.json", "draft_content.json", "template-2.tmp")]
    out += glob.glob(os.path.join(proj, "Timelines", "*", "draft_info.json")) + glob.glob(os.path.join(proj, "Timelines", "*", "template-2.tmp"))
    return [f for f in out if os.path.exists(f)]


def fix(j, check):
    texts = {m["id"]: m for m in j["materials"].get("texts", [])}
    base = None
 # 정상 자막 스타일 하나: 글꼴 경로 + 외곽선이 있고, 자막 프리셋(presets/자막_기본.json)과 같은 글꼴 id인 것.
 # (text-ranges가 지운 범위 스타일은 글꼴 경로가 비어 걸러진다. 제목 글꼴은 id가 달라 걸러진다)
    cap_font = (json.load(open(f"{SKILL}/presets/자막_기본.json"))["style"].get("font_resource_id") or "")
    cands = []
    for m in texts.values():
        c = json.loads(m["content"])
        st = c.get("styles", [])
        if len(st) == 1 and (st[0].get("font") or {}).get("path") and st[0].get("strokes") and st[0].get("size") == 12:
            cands.append(st[0])
    for s0 in cands:
        if cap_font and cap_font in json.dumps(s0):
            base = s0
            break
    if base is None and cands:
        base = cands[0]
    title = json.load(open(f"{SKILL}/presets/제목_노랑.json"))["style"]
    n = {"range_style": 0, "title": 0, "line_width": 0}
    for t in j["tracks"]:
        if t["type"] != "text":
            continue
        for s in t["segments"]:
            m = texts[s["material_id"]]
            c = json.loads(m["content"])
            changed = False
            is_title = "\n" in c.get("text", "") or "DoHyeon" in json.dumps(c.get("styles", []))
            for st in c.get("styles", []):
                if is_title:
                    if not st.get("strokes"):
                        n["title"] += 1
                        if not check:
                            st["strokes"] = [{"width": title["border_width"], "mode": 0, "content": {"solid": {"color": [0, 0, 0]}, "render_type": "solid"}}]
 # 그림자 번짐은 0.06 — 0.25면 제목을 키웠을 때 머리 위로 큰 검은 얼룩(한 편집 사례)
                            st["shadows"] = [{"thickness_projection_distance": 0, "diffuse": 0.06, "angle": -180, "thickness_projection_enable": False,
                                              "content": {"solid": {"color": [0, 0, 0]}, "render_type": "solid"}, "distance": 0,
                                              "thickness_projection_angle": -45, "alpha": title.get("shadow_alpha", 0.9)}]
                            st.setdefault("font", {})["id"] = title.get("font_resource_id", "")
                            if not st["font"].get("path"):
                                st["font"]["path"] = title["font_path"]
                            changed = True
                elif base and (not (st.get("font") or {}).get("path") or not st.get("strokes")):
                    n["range_style"] += 1
                    if not check:
                        for k in ("font", "strokes", "shadows", "useLetterColor"):
                            if k in base:
                                st[k] = json.loads(json.dumps(base[k]))
                        changed = True
            if changed:
                m["content"] = json.dumps(c, ensure_ascii=False)
            if not is_title and m.get("line_max_width") is not None and m["line_max_width"] < 1.0:
                n["line_width"] += 1
                if not check:
                    m["line_max_width"] = 1.0
    return n


def main(proj, check=False):
    if pu.capcut_running() and not check:
        sys.exit("CapCut이 켜져 있다 — 끄고 다시.")
    total = None
    for f in files(proj):
        try:
            j = json.load(open(f))
        except json.JSONDecodeError:
            print(f"건너뜀(JSON 아님): {f}")
            continue
        n = fix(j, check)
        total = total or n
        if not check:
            json.dump(j, open(f, "w"), ensure_ascii=False)
        print(os.path.relpath(f, proj), n)
    if check and total and any(total.values()):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], "--check" in sys.argv)
