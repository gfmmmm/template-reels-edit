#!/usr/bin/env python3
"""CapCut 프로젝트 읽기 전용 분석 — 정답지(사용자가 직접 편집한 프로젝트)의 편집 습관을 숫자로 뽑는다.

사용법: project_profile.py <CapCut 프로젝트 폴더> <출력폴더>
출력: profile.json(조각별 전체), profile.md(사람이 읽는 표 + 통계)
원본은 읽기만 한다. 활성 타임라인(Timelines/project.json의 main_timeline_id)을 따른다.
"""
import json
import os
import statistics as st
import subprocess
import sys
from pathlib import Path

US = 1_000_000


def load(proj):
    p = Path(proj)
    tl = p / "Timelines" / "project.json"
    if tl.exists():
        main = json.load(open(tl))["main_timeline_id"]
        f = p / "Timelines" / main / "draft_info.json"
        if f.exists():
            return json.load(open(f))
    for name in ("draft_content.json", "draft_info.json"):
        if (p / name).exists():
            return json.load(open(p / name))
    sys.exit("타임라인 파일을 못 찾음")


def font_name(path):
    if not path or not os.path.exists(path):
        return None
    r = subprocess.run(["fc-scan", "--format", "%{family}", path], capture_output=True, text=True)
    return r.stdout.strip() or os.path.basename(os.path.dirname(os.path.dirname(path)))


def rgb_hex(c):
    return "#" + "".join(f"{round(x * 255):02x}" for x in c[:3])


def kf_summary(seg):
    out = []
    for k in seg.get("common_keyframes") or []:
        pts = [(round(x["time_offset"] / US, 2), [round(v, 3) for v in x["values"]]) for x in k["keyframe_list"]]
        out.append({"prop": k["property_type"].replace("KFType", ""), "points": pts})
    return out


def main(proj, outdir):
    d = load(proj)
    m = d["materials"]
    by_id = {}
    for kind, items in m.items():
        if isinstance(items, list):
            for x in items:
                if isinstance(x, dict) and "id" in x:
                    by_id[x["id"]] = (kind, x)
    tracks = []
    for ti, t in enumerate(d["tracks"]):
        segs = []
        for s in t["segments"]:
            kind, mat = by_id.get(s.get("material_id"), (None, {}))
            tr = s["target_timerange"]
            clip = s.get("clip") or {}
            row = {
                "start": round(tr["start"] / US, 3), "dur": round(tr["duration"] / US, 3),
                "speed": round(s.get("speed", 1), 3), "volume": round(s.get("volume", 1), 3),
                "src_in": round((s.get("source_timerange") or {}).get("start", 0) / US, 3),
                "kind": kind, "name": mat.get("name") or mat.get("material_name") or os.path.basename(mat.get("path", "")),
                "scale": round((clip.get("scale") or {}).get("x", 1), 3),
                "pos": [round((clip.get("transform") or {}).get("x", 0), 3), round((clip.get("transform") or {}).get("y", 0), 3)],
                "keyframes": kf_summary(s),
            }
            extras = [by_id.get(r) for r in s.get("extra_material_refs", [])]
            row["transition"] = [x[1].get("name") for x in extras if x and x[0] == "transitions"]
            row["animations"] = [a.get("name") or a.get("type") for x in extras if x and x[0] == "material_animations"
                                 for a in x[1].get("animations", [])]
            if kind == "texts":
                c = json.loads(mat.get("content") or "{}")
                row["text"] = c.get("text", "")
                row["styles"] = [{
                    "range": sty.get("range"), "color": rgb_hex(sty["fill"]["content"]["solid"]["color"]) if sty.get("fill") else None,
                    "size": sty.get("size"), "bold": sty.get("bold"),
                    "stroke": [round(x.get("width", 0), 3) for x in sty.get("strokes", [])],
                    "shadow": [round(x.get("alpha", 0), 2) for x in sty.get("shadows", [])],
                    "font": font_name((sty.get("font") or {}).get("path")),
                } for sty in c.get("styles", [])]
                row["background"] = {"alpha": mat.get("background_alpha"), "color": mat.get("background_color"),
                                     "style": mat.get("background_style")}
            segs.append(row)
        tracks.append({"index": ti, "type": t["type"], "segments": segs})
    os.makedirs(outdir, exist_ok=True)
    json.dump({"duration": round(d.get("duration", 0) / US, 3), "fps": d.get("fps"), "tracks": tracks},
              open(f"{outdir}/profile.json", "w"), ensure_ascii=False, indent=1)

    L = [f"# 프로젝트 분석: {os.path.basename(proj.rstrip('/'))}", "",
         f"길이 {round(d.get('duration', 0) / US, 2)}초, fps {d.get('fps')}", ""]
    for t in tracks:
        segs = t["segments"]
        durs = [s["dur"] for s in segs]
        L.append(f"## 트랙 {t['index']} ({t['type']}) — {len(segs)}조각"
                 + (f", 길이 중앙값 {st.median(durs):.2f}초, 평균 {st.mean(durs):.2f}초" if durs else ""))
        L.append("")
        if t["type"] == "text":
            L.append("| 시작 | 길이 | 글자 | 글자수 | 색(범위) | 크기 | 외곽선 | 그림자 | 글꼴 | 배율 | 위치 | 움직임 |")
            L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
            for s in segs:
                cols = " ".join(f"{x['color']}{x['range']}" for x in s.get("styles", []))
                st0 = (s.get("styles") or [{}])[0]
                L.append(f"| {s['start']} | {s['dur']} | {s.get('text','').replace(chr(10),' / ')} | {len(s.get('text','').replace(' ',''))} | {cols} | {st0.get('size')} | {st0.get('stroke')} | {st0.get('shadow')} | {st0.get('font')} | {s['scale']} | {s['pos']} | {', '.join(s['animations'])} |")
        else:
            L.append("| 시작 | 길이 | 배속 | 원본 위치 | 소스 | 배율 | 위치 | 키프레임 | 전환 |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for s in segs:
                kf = "; ".join(f"{k['prop']} " + " → ".join(f"{p[0]}s:{p[1][0]}" for p in k["points"]) for k in s["keyframes"])
                L.append(f"| {s['start']} | {s['dur']} | {s['speed']} | {s['src_in']} | {s['name']} | {s['scale']} | {s['pos']} | {kf} | {', '.join(s['transition'])} |")
        L.append("")
    open(f"{outdir}/profile.md", "w").write("\n".join(L) + "\n")
    print(f"{outdir}/profile.md")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
