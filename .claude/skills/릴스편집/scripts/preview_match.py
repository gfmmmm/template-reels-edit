#!/usr/bin/env python3
"""승인본을 보여 주기 전에 — 확인본(승인본) 화면 값과 CapCut 프로젝트 값을 숫자로 맞춰 본다(공용 규칙).
왜: 승인본은 CapCut이 아니라 Remotion·ffmpeg로 따로 그린 화면이라, 같은 자막이라도 위치·크기가 어긋날 수 있다.
 어긋난 채 승인받으면 CapCut에서 내보낼 때 다른 화면이 나온다(10/9 자막이 실물에서 더 크게 나옴).
사용법: preview_match.py <결과폴더> <CapCut 프로젝트> (capcut_finish 뒤, 승인본을 띄우기 전에)
보는 것: 자막·이모지·라벨·메모·상단 제목의 세로 위치(px, 좌우 25px 안), 이모지·라벨·메모가 "일반 글자" 종류인지, 이모지 그림자,
 확인본 카드(broll-plan)와 CapCut 자료화면 조각의 시작·길이(1프레임 안), 구워 넣기 대상(투명 카드)이 남아 있지 않은지.
결과: 표를 찍고 [결과폴더]/승인전_대조.md. 하나라도 ✗면 끝 코드 1 — 고친 뒤 다시 돌려 ✓만 남으면 승인본을 띄운다.
"""
import glob
import json
import os
import subprocess
import sys

TOL = 25  # px
FR = 1 / 30


def load_project(proj):
    tl = sorted(glob.glob(f"{proj}/Timelines/*/draft_info.json"), key=os.path.getmtime)
    path = tl[-1] if tl else f"{proj}/draft_content.json"
    return json.load(open(path)), path


def ypx(y):  # CapCut transform y(-1~1, 위가 +) → 화면 위에서 px(1920 기준, 가운데)
    return round(960 - y * 960)


def main(res, proj):
    d, src = load_project(proj)
    props = json.load(open(f"{res}/preview/overlay_props.json"))
    rows, bad = [], 0

    def row(item, prev, cap, ok, note=""):
        nonlocal bad
        bad += 0 if ok else 1
        rows.append(f"| {item} | {prev} | {cap} | {'✓' if ok else '✗'} {note} |")

    texts = {m["id"]: m for m in d["materials"]["texts"]}
    segs = []
    for t in d["tracks"]:
        if t["type"] != "text":
            continue
        for s in t["segments"]:
            m = texts.get(s["material_id"], {})
            try:
                txt = json.loads(m.get("content", "{}")).get("text", "")
            except Exception:
                txt = ""
            segs.append((t.get("name", ""), txt, s, m))
    def is_emoji(x):
        x = x.replace("️", "").replace("‍", "").strip()
        return bool(x) and all(0x1F000 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF for c in x)

 # 자막 세로 위치: 확인본 captionTop(기본 1120) = 자막 가운데
    cap_top = props.get("captionTop", 1120)
    caps = [x for x in segs if x[0] != "상단제목" and not is_emoji(x[1]) and x[3].get("type") == "subtitle"]
    ys = sorted({ypx(s["clip"]["transform"]["y"]) for _, _, s, _ in caps})
    normal = [y for y in ys if abs(y - cap_top) <= 200]
    for y in sorted(set(normal)):
        row("자막 세로 위치", f"{cap_top}px", f"{y}px", abs(y - cap_top) <= TOL)
    if not caps:
        row("자막", "있음", "없음", False)
 # 이모지·라벨·메모: 위치·종류·그림자
    ovs = props.get("overlays", [])
    for o in ovs:
        want = round(960 - o["y"] * 960)
        hit = [x for x in segs if x[1] == o["text"]]
        if not hit:
            row(f"{o['kind']} {o['text']}", f"{want}px", "CapCut에 없음", False)
            continue
        _, _, s, m = hit[0]
        got = ypx(s["clip"]["transform"]["y"])
        row(f"{o['kind']} {o['text']} 위치", f"{want}px", f"{got}px", abs(got - want) <= TOL)
        row(f"{o['kind']} {o['text']} 종류", "일반 글자", "일반 글자" if m.get("type") == "text" else "자막(같이 움직임)", m.get("type") == "text")
        if o["kind"] == "emoji":
            sh = json.loads(m.get("content", "{}")).get("styles", [{}])[0].get("shadows") or []
            row(f"이모지 {o['text']} 그림자", "있음", "있음" if sh and sh[0].get("alpha", 0) >= 0.5 else "없음/흐림", bool(sh) and sh[0].get("alpha", 0) >= 0.5)
 # 상단 제목
    if props.get("title"):
        t = [x for x in segs if x[0] == "상단제목"]
        row("상단 제목", "있음", "있음" if t else "없음", bool(t))
 # 자료화면 카드 시작·길이
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    cardsegs = []
    for t in d["tracks"]:
        if t["type"] == "video" and t.get("name", "") != "인물":  # 자료화면 트랙(사용자가 옮겨 이름이 비어도 찾는다)
            for s in t["segments"]:
                cardsegs.append((os.path.basename(vids[s["material_id"]]["path"]).split(".")[0], s))
    for c in json.load(open(f"{res}/broll-plan.json"))["cards"]:
        hit = [s for n, s in cardsegs if n == c["id"]]
        if not hit:
            row(f"자료화면 {c['id']}", f"{c['start']:.2f}초", "CapCut에 없음", False)
            continue
        st = hit[0]["target_timerange"]["start"] / 1e6
        row(f"자료화면 {c['id']} 시작", f"{c['start']:.2f}초", f"{st:.2f}초", abs(st - c["start"]) <= FR + 0.001)
        alpha = f"{res}/cards/{c['id']}.mov"
        pf = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", alpha],
                            capture_output=True, text=True).stdout.strip()
        if c.get("component") in ("FaceScan", "IconPop", "PercentBar") and pf.startswith("yuva"):
            row(f"자료화면 {c['id']} 투명", "구워 넣음", "투명 그대로", False, "— bake_overlay.py (CapCut이 반투명을 뭉갬)")
    out = ["# 승인 전 대조 (확인본 ↔ CapCut 프로젝트)", "", f"프로젝트 파일: {src}", "",
           "| 항목 | 확인본 | CapCut | 결과 |", "|---|---|---|---|"] + rows + ["", f"✗ {bad}개" if bad else "전부 ✓ — 승인본을 띄워도 된다"]
    open(f"{res}/승인전_대조.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
