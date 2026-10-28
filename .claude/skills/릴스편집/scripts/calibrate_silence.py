#!/usr/bin/env python3
"""무음 감지 기준값 보정 — 정답지에서 사용자가 남긴 구간과 detect-silence 결과가 가장 잘 맞는 값을 찾는다.

사용법: calibrate_silence.py <profile.json> <원본 영상> <원본 파일명 일부> <출력.json>
- profile.json: project_profile.py 결과
- 비교 범위: 정답지가 실제로 쓴 원본 구간 근처만(내용 때문에 통째로 버린 구간은 무음 판단과 무관)
- 점수: 남긴 구간 ↔ 감지된 말 구간의 겹침(IoU)
"""
import itertools
import json
import os
import subprocess
import sys
import tempfile


def kept_spans(profile, key):
    spans = []
    for t in profile["tracks"]:
        for s in t["segments"]:
            if key in (s.get("name") or ""):
                spans.append((s["src_in"], s["src_in"] + s["dur"] * s["speed"]))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def regions(kept, join=3.0, margin=1.0):
    """정답지가 쓴 구간을 3초 안쪽 간격끼리 묶어 비교 범위로 삼는다."""
    out = []
    for a, b in kept:
        if out and a - out[-1][1] <= join:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [(max(0, a - margin), b + margin) for a, b in out]


def detect(video, th, ms, pad):
 # capcut-cli는 파이프로 받으면 64KB에서 잘린다 → 파일로 받는다
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:
        subprocess.run(["capcut", "detect-silence", video, "--threshold-db", str(th),
                        "--min-silence", str(ms), "--pad", str(pad)], stdout=fh)
    d = json.load(open(tmp))
    os.unlink(tmp)
    keep = d.get("keeps") or d.get("keep") or []
    return [(k["start"], k["end"]) for k in keep]


def length_in(spans, regs):
    tot = 0.0
    for a, b in spans:
        for ra, rb in regs:
            tot += max(0.0, min(b, rb) - max(a, ra))
    return tot


def inter(x, y):
    out = []
    for a, b in x:
        for c, d in y:
            lo, hi = max(a, c), min(b, d)
            if hi > lo:
                out.append((lo, hi))
    return out


def main(profile_path, video, key, out):
    prof = json.load(open(profile_path))
    kept = kept_spans(prof, key)
    regs = regions(kept)
    kept_len = length_in(kept, regs)
    results = []
    for th, ms, pad in itertools.product([-45, -40, -35, -30, -25], [0.15, 0.2, 0.3, 0.4, 0.5], [0.0, 0.05, 0.1, 0.15]):
        det = detect(video, th, ms, pad)
        det_len = length_in(det, regs)
        both = length_in(inter(det, kept), regs)
        iou = both / (det_len + kept_len - both) if det_len + kept_len else 0
        results.append({"threshold_db": th, "min_silence": ms, "pad": pad, "iou": round(iou, 3),
                        "detected_s": round(det_len, 1), "kept_s": round(kept_len, 1)})
    results.sort(key=lambda r: -r["iou"])
    gaps = [round(b[0] - a[1], 2) for a, b in zip(kept, kept[1:]) if 0 < b[0] - a[1] <= 3.0]
    json.dump({"best": results[0], "top5": results[:5], "kept_spans": len(kept),
               "removed_gaps_s": sorted(gaps)}, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(results[:5], ensure_ascii=False))
    print("잘라낸 짧은 틈(초):", sorted(gaps))


if __name__ == "__main__":
    main(*sys.argv[1:5])
