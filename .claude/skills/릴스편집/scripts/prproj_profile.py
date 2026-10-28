#!/usr/bin/env python3
"""1단계 정답지가 Premiere 프로젝트(.prproj)일 때 — 편집자가 한 일을 숫자로 뽑는다(한 생활용품 계정 정답지 대조에서 만듦).
CapCut 정답지는 project_profile.py, Premiere 는 이 스크립트.

사용법: prproj_profile.py <프로젝트.prproj> <출력폴더> [--seq "시퀀스 이름"] [--media <원본 폴더>]
 --seq 없으면 트랙·글자가 가장 많은 시퀀스(완성본). --media 를 주면 말 사이 틈을 원본 소리로 잰다(편집자가 남긴 무음).
출력: <출력폴더>/prproj_profile.md (사람용), prproj_profile.json
 - 트랙별 조각: 시작·끝(초), 원본 파일·원본 시작, 배속, 확대(비율 조정 ÷ 기본 비율)·위치, 효과(흔들림 안정화·Lumetri 등)
 - 글자: 트랙·시각·글꼴·글자·위치·크기·효과(시간 포스터화+뒤틀기 변위 = 손글씨처럼 떨림)
 - 소리: 효과음 파일·시각, 대사 트랙 수
 - 중첩 시퀀스 안(사진 틀·끝 문구 등)도 한 단계 풀어서
 - 요약: 자막 수·글꼴 종류·효과음 개수와 초당 개수·확대 횟수와 배율·말 사이 틈 중앙값
"""
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

TICK = 254016000000


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        import gzip
        raw = gzip.decompress(raw)
    root = ET.fromstring(raw)
    byid = {e.attrib["ObjectID"]: e for e in root if "ObjectID" in e.attrib}
    byuid = {e.attrib["ObjectUID"]: e for e in root if "ObjectUID" in e.attrib}

    def ref(el):
        if el is None:
            return None
        if "ObjectRef" in el.attrib:
            return byid.get(el.attrib["ObjectRef"])
        if "ObjectURef" in el.attrib:
            return byuid.get(el.attrib["ObjectURef"])
        return None
    return root, ref


def sec(x):
    return round(int(x) / TICK, 3) if x not in (None, "") else None


def first_val(pe):
    v = pe.findtext("StartKeyframe")
    kf = pe.findtext("Keyframes")
    if kf:
        return "KF:" + kf[:120]
    if v and "," in v:
        return v.split(",")[1]
    return v


def text_blob(b64):
    t = base64.b64decode(b64 or "").decode("utf-8", "ignore")
    words = re.findall(r"[가-힣A-Za-z0-9 .,?!~…\[\]\(\)'\"%:/-]+", t)
    fonts = [w for w in words if re.match(r"^[A-Z][A-Za-z0-9-]{5,}$", w)]
    kor = " ".join(w.strip() for w in words if re.search("[가-힣]", w))
    return (fonts[:1] or [""])[0], kor


def components(ref, cti):
    out = []
    ch = ref(cti.find("ComponentOwner/Components"))
    if ch is None:
        return out
    for c in ch.iter("Component"):
        ce = ref(c)
        if ce is None:
            continue
        d = {"name": ce.findtext(".//DisplayName") or "", "match": ce.findtext(".//MatchName") or "", "params": {}}
        for p in ce.iter("Param"):
            pe = ref(p)
            if pe is None:
                continue
            nm = (pe.findtext("Name") or "").strip()
            if pe.tag == "ArbVideoComponentParam" and nm == "소스 텍스트":
                d["font"], d["text"] = text_blob(pe.findtext("StartKeyframeValue"))
            elif nm and nm not in d["params"]:
                v = first_val(pe)
                if v is not None:
                    d["params"][nm] = v
        out.append(d)
    return out


def media(ref, sub):
    info = {"name": sub.findtext("Name")}
    clip = ref(sub.find("Clip"))
    cl = clip.find("Clip") if clip is not None else None
    if cl is None:
        return info
    info["src_in"] = sec(cl.findtext("InPoint"))
    sp = cl.findtext("PlaybackSpeed")
    info["speed"] = float(sp) if sp else 1.0
    src = ref(cl.find("Source"))
    if src is not None:
        m = src.find(".//Media")
        me = ref(m) if m is not None else None
        if me is not None:
            info["file"] = os.path.basename(me.findtext("FilePath") or "")
        sq = src.find(".//Sequence")
        if sq is not None and ref(sq) is not None:
            info["nested"] = ref(sq).findtext("Name")
    return info


def sequence(root, ref, name):
    seq = [e for e in root if e.tag == "Sequence" and e.findtext("Name") == name][0]
    tracks = []
    for tg in seq.find("TrackGroups").findall("TrackGroup"):
        g = ref(tg.find("Second"))
        kind = "video" if g.tag.startswith("Video") else "audio"
        for ti, tr in enumerate(g.iter("Track")):
            te = ref(tr)
            if te is None:
                continue
            items = []
            for it in te.iter("TrackItem"):
                ie = ref(it)
                if ie is None or ie.tag not in ("VideoClipTrackItem", "AudioClipTrackItem"):
                    continue
                cti = ie.find("ClipTrackItem")
                d = {"start": sec(cti.findtext("TrackItem/Start") or "0"), "end": sec(cti.findtext("TrackItem/End"))}
                sub = ref(cti.find("SubClip"))
                if sub is not None:
                    d.update(media(ref, sub))
                d["fx"] = components(ref, cti)
                items.append(d)
            if items:
                tracks.append({"kind": kind, "index": ti, "items": items})
    return tracks


def seq_len(root, ref, name):
    return max((it["end"] or 0) for t in sequence(root, ref, name) for it in t["items"])


def gaps_by_sound(tracks, media_dir, th=-38.0):
    import numpy as np
    items = sorted([it for t in tracks if t["kind"] == "audio" and t["index"] == 0 for it in t["items"] if it.get("file")],
                   key=lambda x: x["start"])
    rows = []
    for it in items:
        path = os.path.join(media_dir, it["file"])
        if not os.path.exists(path):
            cand = [f for f in os.listdir(media_dir) if os.path.splitext(f)[0].lower() == os.path.splitext(it["file"])[0].lower()]
            if not cand:
                continue
            path = os.path.join(media_dir, cand[0])
        sp = it.get("speed") or 1.0
        a = it["src_in"]
        b = a + (it["end"] - it["start"]) * sp
        out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", path, "-vn", "-ac", "1",
                              "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(out, np.int16).astype(float) / 32768
        e = [20 * np.log10(np.sqrt((x[i:i + 160] ** 2).mean()) + 1e-9) for i in range(0, max(0, len(x) - 160), 160)]
        loud = [i for i, v in enumerate(e) if v > th]
        if loud:
            rows.append((loud[0] * 0.01 / sp, (len(e) - 1 - loud[-1]) * 0.01 / sp))
    return [round(x[1] + y[0], 2) for x, y in zip(rows, rows[1:])]


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    root, ref = load(path)
    names = [e.findtext("Name") for e in root if e.tag == "Sequence"]
    def richness(n):  # 완성본 = 트랙·글자가 가장 많은 시퀀스(가장 긴 것은 편집 전 고르기 시퀀스일 때가 많다)
        tr = sequence(root, ref, n)
        return (len(tr), sum(1 for t in tr for it in t["items"] for f in it["fx"] if f.get("text")))
    name = arg("--seq") or max(names, key=richness)
    tracks = sequence(root, ref, name)
    nested = {}
    for t in tracks:
        for it in t["items"]:
            if it.get("nested") and it["nested"] not in nested:
                nested[it["nested"]] = sequence(root, ref, it["nested"])
    base = None  # 기본 비율 = 가장 흔한 비율 조정 값(4K 원본이면 50)
    scales = [float(f["params"]["비율 조정"]) for t in tracks if t["kind"] == "video" for it in t["items"] for f in it["fx"]
              if f["name"] == "모션" and re.match(r"^[\d.]+$", f["params"].get("비율 조정", ""))]
    if scales:
        base = statistics.mode(scales)
    L = [f"# Premiere 정답지 — {os.path.basename(path)} / 시퀀스 \"{name}\"\n"]
    texts, sfx, zooms = [], [], []
    for t in tracks:
        L.append(f"\n## {t['kind']} {t['index']}\n\n| 시작 | 끝 | 소재 | 원본 시작 | 배속 | 확대·위치 | 효과 | 글자 |\n|---|---|---|---|---|---|---|---|")
        for it in t["items"]:
            mo = next((f for f in it["fx"] if f["name"] == "모션"), None)
            zoom = ""
            if mo and base and (it.get("file") or it.get("nested")) and not any(f.get("text") for f in it["fx"]):  # 글자 그래픽 비율은 확대가 아니다
                sc = mo["params"].get("비율 조정", "")
                if re.match(r"^[\d.]+$", sc) and abs(float(sc) - base) > 0.5:
                    zoom = f"{float(sc) / base:.2f}배 @{mo['params'].get('위치', '')}"
                    zooms.append((it["start"], round(float(sc) / base, 2)))
                elif sc.startswith("KF:"):
                    zoom = "움직임 " + sc[:60]
            fxn = ", ".join(sorted({f["name"] for f in it["fx"] if f["name"] not in ("모션", "텍스트", "벡터 모션")}))
            tx = " / ".join(f"{f.get('font', '')}: {f.get('text', '')}" for f in it["fx"] if f.get("text"))
            if tx:
                texts.append((it["start"], it["end"], tx, fxn))
            if t["kind"] == "audio" and it.get("file") and not it["file"].lower().startswith("img_"):
                sfx.append((it["start"], it["file"]))
            L.append(f"| {it['start']} | {it['end']} | {it.get('nested') or it.get('file') or it.get('name')} | {it.get('src_in')} | "
                     f"{it.get('speed', 1)} | {zoom} | {fxn} | {tx} |")
    for nm, tr in nested.items():
        L.append(f"\n## 중첩 시퀀스 \"{nm}\"\n")
        for t in tr:
            for it in t["items"]:
                mo = next((f for f in it["fx"] if f["name"] == "모션"), None)
                tx = " / ".join(f"{f.get('font', '')}: {f.get('text', '')}" for f in it["fx"] if f.get("text"))
                L.append(f"- {t['kind']} {t['index']} {it['start']}~{it['end']} {it.get('file') or it.get('name')} "
                         f"{('비율 ' + mo['params'].get('비율 조정', '')) if mo else ''} {tx}")
    dur = max((it["end"] or 0) for t in tracks for it in t["items"])
    fonts = sorted({x.split(":")[0] for _, _, tx, _ in texts for x in tx.split(" / ") if x.split(":")[0]})
    summary = {"sequence": name, "duration": dur, "text_items": len(texts), "fonts": fonts, "sfx": len(sfx),
               "sfx_per_sec": round(len(sfx) / dur, 3) if dur else 0, "zooms": zooms, "base_scale": base}
    if arg("--media"):
        g = gaps_by_sound(tracks, arg("--media"))
        if g:
            summary["gap_median"] = statistics.median(g)
            summary["gap_max"] = max(g)
    L.insert(1, "\n## 요약\n\n" + "\n".join(f"- {k}: {v}" for k, v in summary.items()) +
             "\n\n### 글자\n" + "\n".join(f"- {a}~{b} {tx} ({fx})" for a, b, tx, fx in texts) +
             "\n\n### 효과음\n" + "\n".join(f"- {a} {f}" for a, f in sfx) + "\n")
    open(os.path.join(outdir, "prproj_profile.md"), "w", encoding="utf-8").write("\n".join(L))
    json.dump({"summary": summary, "tracks": tracks, "nested": nested}, open(os.path.join(outdir, "prproj_profile.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
