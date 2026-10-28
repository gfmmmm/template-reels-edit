#!/usr/bin/env python3
"""3단계 마무리 — compile로 못 넣는 것: 상단 제목, 자막 부분 칠하기·큰 자막 색, 이모지·라벨·메모, 장면 전환, 효과음 크기.

사용법: capcut_finish.py <결과폴더> <CapCut 프로젝트>
- 상단 제목: title.txt (두 줄이면 줄바꿈 그대로), title_dur.txt(첫 훅 문장 끝 시각) → add-text --preset presets/제목_노랑.json --track-name 상단제목
- 자막 색 범위: captions.json의 ranges(노랑 부분 칠하기)·big+색 → capcut text-ranges
- overlays.json: [{"kind": "emoji"|"label"|"memo", "text", "start", "end", "x", "y"}] → presets/templates/이모지_흔들림·라벨_흔들림·메모_노랑
 (정답지에서 떠낸 조각이라 흔들림 애니메이션·글꼴·크기가 따라온다), apply-template --x --y
- transition.json: {"at": 편집본 시각, "slug": "rollup-slide"} → 그 시각에서 끝나는 인물 조각에 capcut transition
- 효과음 크기: sfx_volumes.json의 시작 시각으로 오디오 조각을 찾아 capcut volume
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = f"{SKILL}/presets/templates"
YELLOW = "#F4C70F"  # 템플릿을 못 읽을 때만 쓰는 기본값


def _tpl_color(name, default):
    """자막 색은 계정 템플릿(presets/templates)에서 읽는다 — 계정마다 노랑·빨강이 다르다(2026-10-26 한 생활용품 계정 #EAF06C)."""
    try:
        return json.load(open(f"{TPL}/{name}.json"))["material"]["data"]["text_color"].upper()
    except Exception:
        return default


def _big_size(default=21.3):
    """크게 자막 글자 크기도 계정 템플릿 값(자막_크게)을 쓴다."""
    try:
        c = json.loads(json.load(open(f"{TPL}/자막_크게.json"))["material"]["data"]["content"])
        return float(c["styles"][0]["size"])
    except Exception:
        return default
KIND_TPL = {"emoji": "이모지_흔들림", "label": "라벨_흔들림", "memo": "메모_노랑"}


def cli(*a):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:
        subprocess.run(["capcut", *a], stdout=fh)
    t = open(tmp).read()
    os.unlink(tmp)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {"raw": t}


def segs_of(proj, kind):
    s = cli("segments", proj, "--track", kind)
    return s if isinstance(s, list) else s.get("segments", [])


def main(res, proj):
    if pu.capcut_running():
        sys.exit("CapCut이 켜져 있다.")
    end = max(s["start"] + s["duration"] for s in json.load(open(f"{res}/timemap.json")))
    done = {}
    if os.path.exists(f"{res}/title.txt"):
        title = open(f"{res}/title.txt").read().strip()
 # 상단 제목은 첫 훅 문장 동안만(사용자 지시) — 영상 내내 띄우지 않는다. 영상마다 모양을 바꾸면 [결과폴더]/title_preset.json(가로 배치판처럼 흰 글자 내내)
        dur = float(open(f"{res}/title_dur.txt").read()) if os.path.exists(f"{res}/title_dur.txt") else 3.0
        r = cli("add-text", proj, "0", f"{min(dur, end):.3f}", title, "--preset", (f"{res}/title_preset.json" if os.path.exists(f"{res}/title_preset.json") else f"{SKILL}/presets/제목_노랑.json"),
                "--track-name", "상단제목")
        done["title"] = r.get("ok", r)
 # 프리셋은 위치만 바꾸고 배율은 안 바꾼다 → 키프레임 두 개(같은 값)로 배율 고정. 레퍼런스 제목 글자 높이 약 106px
        sid = r.get("segment_id")
 # 크기·위치: 사용자 기존 영상처럼 크게(— 1.58은 작다). 배율이 커지면 가운데 기준으로 위아래로 커지므로 위치도 같이
        scale = float(open(f"{res}/title_scale.txt").read()) if os.path.exists(f"{res}/title_scale.txt") else 1.98
        ty = float(open(f"{res}/title_y.txt").read()) if os.path.exists(f"{res}/title_y.txt") else 0.654
        if sid:
            for tm in (0, round(min(dur, end) - 0.05, 3)):
                cli("keyframe", proj, sid, "scale_x", str(tm), str(scale), "-q")
                cli("keyframe", proj, sid, "position_y", str(tm), str(ty), "-q")

 # 자막 색 범위 (부분 칠하기, 큰 자막의 색)
    caps = json.load(open(f"{res}/captions.json"))
    texts = segs_of(proj, "text")
    n_rng = 0
    for c in caps:
        if c.get("hidden") or not (c.get("ranges") or (c.get("big") and c["color"] != "white")):
            continue
        hit = [s for s in texts if abs(s["start_us"] / 1e6 - c["start"]) < 0.02 and s.get("label") == c["text"]]
        if not hit:
            continue
        if c.get("ranges"):
            st = [{"start": a, "end": b, "font_color": _tpl_color("자막_노랑", YELLOW)} for a, b in c["ranges"]]
        else:
            st = [{"start": 0, "end": len(c["text"]),
                   "font_color": _tpl_color("자막_노랑", YELLOW) if c["color"] == "yellow" else _tpl_color("자막_빨강", "#EC1D1D")}]
        if c.get("big"):  # 크게 템플릿의 글자 크기를 범위에도 그대로
            st = [dict(x, font_size=_big_size()) for x in st]
        cli("text-ranges", proj, hit[0]["id"], "--styles", json.dumps(st))
        n_rng += 1
    done["text_ranges"] = n_rng

 # 이모지·라벨·메모
    n_ov = 0
    if os.path.exists(f"{res}/overlays.json") and "--overlays" in sys.argv:  # 기본은 build_spec이 compile로 넣는다
        for o in json.load(open(f"{res}/overlays.json")):
            r = cli("apply-template", proj, f"{TPL}/{o.get('tpl') or KIND_TPL[o['kind']]}.json", f"{o['start']:.3f}",
                    f"{o['end'] - o['start']:.3f}", o["text"], "--x", str(o["x"]), "--y", str(o["y"]))
            n_ov += 1 if r.get("ok", True) and "error" not in r else 0
        done["overlays"] = n_ov

 # compile은 글자 템플릿을 전부 한 트랙(자막)에 넣는다 → 이모지·라벨·메모를 자막 트랙 밖 위쪽 트랙으로 옮긴다.
 # duplicate --track은 자리가 차 있으면 실패(exit 1) → 다음 트랙, 모두 차면 --new-track. 그다음 원본 삭제.
    if os.path.exists(f"{res}/overlays.json"):
        texts = segs_of(proj, "text")
        moved, ov_tracks = 0, []
        for o in json.load(open(f"{res}/overlays.json")):
            hit = [x for x in texts if x.get("label") == o["text"] and abs(x["start_us"] / 1e6 - o["start"]) < 0.02]
            if not hit:
                continue
            sid, ok = hit[0]["id"], False
            for tn in ov_tracks:
                if subprocess.run(["capcut", "duplicate", proj, sid, "--track", tn], capture_output=True).returncode == 0:
                    ok = True
                    break
            if not ok:
                before = {t["name"] for t in cli("tracks", proj) if t["type"] == "text"}
                subprocess.run(["capcut", "duplicate", proj, sid, "--new-track"], capture_output=True)
                ov_tracks += [t["name"] for t in cli("tracks", proj) if t["type"] == "text" and t["name"] not in before]
            subprocess.run(["capcut", "remove", proj, sid], capture_output=True)
            moved += 1
        done["overlays_moved"] = f"{moved} → 트랙 {len(ov_tracks)}개"

 # 장면 전환 (마무리 구간 시작 컷에 1번)
    if os.path.exists(f"{res}/transition.json"):
        tr = json.load(open(f"{res}/transition.json"))
        vids = segs_of(proj, "video")
        stem = os.path.splitext(os.path.basename(json.load(open(f"{res}/spec.json"))["tracks"][0]["items"][0]["path"]))[0]
        prev = [s for s in vids if abs((s["start_us"] + s["duration_us"]) / 1e6 - tr["at"]) < 0.04
                and stem in (s.get("label") or "")]  # 인물 트랙 조각만
        if prev:
            r = cli("transition", proj, prev[0]["id"], tr.get("slug", "rollup-slide"))
            done["transition"] = r.get("ok", r)

    vols = json.load(open(f"{res}/sfx_volumes.json"))
    segs = segs_of(proj, "audio")
    n = 0
    for v in vols:
        hit = [s for s in segs if abs(s["start_us"] / 1e6 - v["start"]) < 0.02]
        for s in hit:
            cli("volume", proj, s["id"], str(v["volume"]), "-q")
            n += 1
    done["sfx_volume_set"] = f"{n}/{len(vols)}"
 # text-ranges·add-text가 지운 글꼴·외곽선, 좁은 줄 폭을 바로잡는다(③-E-1)
    subprocess.run([sys.executable, f"{SKILL}/scripts/capcut_textfix.py", proj])
 # CapCut이 한 번 연 프로젝트는 Timelines/<id>/ 사본을 연다. 위 단계(제목·트랙 옮기기·색 범위·전환)는 루트에만 써지므로
 # 끝에 루트를 사본으로 복사한다(IMG_0519 2026-10-24: 사본에 상단 제목·이모지 트랙이 빠져 preview_match ✗).
    tl = os.path.join(proj, "Timelines")
    if os.path.isdir(tl):
        import shutil
        for d in os.listdir(tl):
            dd = os.path.join(tl, d)
            if os.path.isfile(os.path.join(dd, "draft_info.json")):
                shutil.copy2(os.path.join(dd, "draft_info.json"), os.path.join(dd, "draft_info.json.bak_finish"))
                shutil.copy2(os.path.join(proj, "draft_content.json"), os.path.join(dd, "draft_info.json"))
                if os.path.exists(os.path.join(proj, "template-2.tmp")):
                    shutil.copy2(os.path.join(proj, "template-2.tmp"), os.path.join(dd, "template-2.tmp"))
                done["timeline_copy"] = d
    print(json.dumps(done, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
