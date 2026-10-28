#!/usr/bin/env python3
"""1단계 게시본 재기 — 사용자가 실제로 올린 완성 영상(게시본)에서 편집메뉴얼 값을 먼저 잰다(공용 규칙 67).
(한 생활용품 계정: 편집자 프로젝트 파일만 읽고 "말 1.0배·인트로 있음·끝 문구 흰색"으로 적었는데 게시본은 1.1배·인트로 없음·
 하늘색이었다. 프로젝트는 게시 전 마지막 판이 아닐 수 있다 → 게시본 값을 (게시본)으로 먼저, 프로젝트 값 (정)은 그다음)

사용법: posted_profile.py <게시본.mp4> <출력폴더> [--source <원본 영상 하나>]
잰 것(출력폴더/posted_profile.md):
 길이, 장면 바뀜(scdet) — 장면 수·가운데 길이·2초 넘는 장면 수, 밝기·채도(signalstats 평균·YLOW·YHIGH·SATAVG),
 소리 크기(ebur128 I·LRA), 배경음악이 깔렸나(말 없는 곳의 바닥 소리가 -40dB 보다 크면 깔렸다고 본다 — 말보다 몇 dB 작은지),
 0.5초 간격 장면 사진 타일(자막 크기·자리·끝 문구는 이 사진으로 직접 잰다)
 --source 를 주면 원본의 밝기·채도도 재서 색 보정 목표 차이를 적는다.
말 배속은 이것으로 못 잰다 — 2단계 ①② 뒤 speed_match.py.
"""
import os
import re
import statistics
import subprocess
import sys

import numpy as np


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def stats(path):
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf",
                          "fps=2,scale=270:-1,signalstats,metadata=print:file=-", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    g = lambda k: round(statistics.mean(float(x) for x in re.findall(rf"lavfi.signalstats.{k}=([0-9.]+)", out)), 1)  # noqa: E731
    return {k: g(k) for k in ("YAVG", "YLOW", "YHIGH", "SATAVG")}


def main(video, out):
    os.makedirs(out, exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout)
    sc = run(["ffmpeg", "-nostdin", "-i", video, "-vf", "scale=270:-1,scdet=threshold=8", "-an", "-f", "null", "-"])
    cuts = [0.0] + [float(x) for x in re.findall(r"lavfi.scd.time: ([0-9.]+)", sc)] + [dur]
    shots = [b - a for a, b in zip(cuts, cuts[1:]) if b - a > 0.05]
    st = stats(video)
    eb = run(["ffmpeg", "-nostdin", "-i", video, "-af", "ebur128", "-f", "null", "-"])
    I = re.findall(r"I:\s+(-?[0-9.]+) LUFS", eb)
    LRA = re.findall(r"LRA:\s+([0-9.]+) LU", eb)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    n = 320
    db = np.array([20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9) for i in range(0, len(x) - n, n)])
    floor, speech = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    bgm = floor > -40
    tile = os.path.join(out, "게시본_0.5초.jpg")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-vf", "fps=2,scale=180:-1,tile=12x6", "-frames:v", "1", tile])
    L = [f"# 게시본 측정 — {os.path.basename(video)}", "",
         "| 항목 | 값 (게시본) |", "|---|---|",
         f"| 길이 | {dur:.2f}초 |",
         f"| 장면 | {len(shots)}개, 가운데 {statistics.median(shots):.2f}초, 2초 넘는 장면 {sum(1 for s in shots if s > 2)}개 |",
         f"| 밝기 | 평균 {st['YAVG']} · 어두운 쪽 {st['YLOW']} · 밝은 쪽 {st['YHIGH']} · 채도 {st['SATAVG']} |",
         f"| 소리 | {I[-1] if I else '?'} LUFS, 크기 변화 폭 {LRA[-1] if LRA else '?'} LU |",
         f"| 배경음악 | {'깔림(추정) — 바닥 소리 %.0fdB, 말(위 10%%)보다 %.0fdB 작게' % (floor, speech - floor) if bgm else '없음(추정) — 바닥 소리 %.0fdB' % floor} |"]
    if "--source" in sys.argv:
        src = stats(sys.argv[sys.argv.index("--source") + 1])
        L.append(f"| 원본 밝기 | 평균 {src['YAVG']} · 어두운 쪽 {src['YLOW']} · 밝은 쪽 {src['YHIGH']} · 채도 {src['SATAVG']} "
                 f"→ 색 보정 목표 차이 평균 {st['YAVG'] - src['YAVG']:+.1f}, 어두운 쪽 {st['YLOW'] - src['YLOW']:+.1f}, 채도 {st['SATAVG'] - src['SATAVG']:+.1f} |")
    L += ["", f"장면 사진: `{tile}` — 자막 크기·자리(인물 장면/손·제품 장면), 강조 크기, 끝 문구 색·크기는 여기서 직접 잰다.",
          "말 배속: 2단계 ①② 뒤 `speed_match.py [결과폴더] <게시본> --audio <편집용 말 영상>`."]
    open(os.path.join(out, "posted_profile.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
