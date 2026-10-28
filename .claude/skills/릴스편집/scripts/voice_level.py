#!/usr/bin/env python3
"""2단계 ③ 문장마다 목소리 크기를 고르게 — 화면 밖 질문자·설명하는 사람·마이크에서 멀어진 문장의 크기 차이를 줄인다
(한 생활용품 계정 시험: 문장 크기 -21.6~-11.6dB, 10dB 차이. 편집자는 질문자 목소리를 따로 트랙에 올려 맞췄다).

사용법: voice_level.py <결과폴더> <편집용 영상> <출력 영상> [--target 자동] [--max 6] [--min-diff 1.5]
입력: timemap.json(문장별 원본 구간 — cutplan 결과)
하는 일: 문장마다 말소리 크기(-40dB 넘는 0.1초 창의 중앙값)를 재고, 전체 중앙값(target)과의 차이만큼 그 문장 구간만 올리거나
 내린다(±max dB 안, 차이가 min-diff 보다 작으면 그대로). 경계는 0.04초 동안 부드럽게. 영상은 그대로 복사.
끝나면 출력 영상으로 cutplan.py 를 다시 돌린다(시간은 그대로라 edge_fix·자막·효과 시간이 바뀌지 않는다). 보고에 문장별 조정 dB 를 적는다.
"""
import json
import subprocess
import sys

import numpy as np


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def level(video, a, b):
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", video, "-vn",
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(out, np.int16).astype(float) / 32768
    e = [20 * np.log10(np.sqrt((x[i:i + 1600] ** 2).mean()) + 1e-9) for i in range(0, max(0, len(x) - 1600), 1600)]
    e = [v for v in e if v > -40]
    return float(np.median(e)) if e else None


def main(res, video, out):
    mx, mind = arg("--max", 6.0), arg("--min-diff", 1.5)
    tm = json.load(open(f"{res}/timemap.json"))
    spans = {}
    for p in tm:
        if p["take"] == 0:  # 인트로(말 없는 행동 장면)는 크기를 맞추지 않는다
            continue
        a, b = spans.get(p["take"], (1e9, -1))
        spans[p["take"]] = (min(a, p["src_in"]), max(b, p["src_out"]))
    lv = {n: level(video, a, b) for n, (a, b) in spans.items()}
    vals = [v for v in lv.values() if v is not None]
    target = arg("--target", float(np.median(vals)))
    parts, report = [], []
    for n, (a, b) in sorted(spans.items(), key=lambda x: x[1][0]):
        if lv[n] is None:
            continue
        g = max(-mx, min(mx, target - lv[n]))
        report.append((n, round(lv[n], 1), round(g, 1)))
        if abs(g) < mind:
            continue
        k = 10 ** (g / 20)
        r = 0.04  # 경계를 부드럽게
        parts.append(f"if(between(t,{a - r:.3f},{b + r:.3f}),"
                     f"1+({k:.4f}-1)*min(1,min((t-{a - r:.3f})/{r},({b + r:.3f}-t)/{r}))")
    expr = "1"
    for p in reversed(parts):
        expr = f"{p},{expr})"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                    "-af", f"volume='{expr}':eval=frame,alimiter=limit=0.89:level=0", "-c:a", "pcm_s16le", out], check=True)
    after = [level(out, a, b) for a, b in spans.values()]
    after = [v for v in after if v is not None]
    print(f"목표 {target:.1f}dB · 문장 크기 차이 {max(vals) - min(vals):.1f} → {max(after) - min(after):.1f}dB")
    for n, l, g in report:
        print(f"  문장 {n}: {l}dB → {'+' if g >= 0 else ''}{g}dB{'' if abs(g) >= mind else ' (그대로)'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
