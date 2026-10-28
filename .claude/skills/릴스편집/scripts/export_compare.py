#!/usr/bin/env python3
"""CapCut 실물 검수 — 사용자가 CapCut에서 내보낸 영상과 확인본(preview/확인본.mp4)을 자막마다 나란히 대조한다.
확인본은 CapCut 자막을 흉내 낸 그림이라 CapCut 실물과 다를 수 있다(첫 편집: 제목 글꼴이 빠져 화면을 넘침,
자막 두 줄 꺾임, 이모지 1/3 크기, 부분 노랑 자막 글꼴 깨짐). 사용자에게 "완성"이라고 하기 전에 반드시 이 대조를 통과한다.

사용법: (opencv 있는 파이썬) export_compare.py <결과폴더> <내보낸 영상>
비교 시점: captions.json 자막마다 가운데 시각 + 이모지마다 가운데 시각
띠별 차이(0~255 평균): 제목(세로 150~450px) / 이름표·자막(950~1200px) / 이모지(1200~1450px)
 - 화면 내용(인물)은 같으니 띠 차이가 크면 글자 모양·위치·크기가 다르다는 뜻
출력: [결과폴더]/export_check/pairs_NN.jpg(왼쪽 실물, 오른쪽 확인본, 6쌍씩), report.md(시점별 띠 차이, 기준 넘는 곳 표시)
기준: 띠 차이 18 이상이면 "다름" — 그 쌍은 반드시 눈으로 보고 원인을 고친다. 길이 차이 0.2초 이상도 표시.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

BANDS = {"제목": (150, 450), "이름표·자막": (950, 1200), "이모지": (1200, 1450)}
LIMIT = 18


def frame(path, t):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", "scale=1080:1920", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.uint8).reshape(1920, 1080, 3) if len(out) == 1920 * 1080 * 3 else None


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


def main(res, exported):
    out = f"{res}/export_check"
    os.makedirs(out, exist_ok=True)
    check = f"{res}/preview/확인본.mp4"
    caps = json.load(open(f"{res}/captions.json"))
    ovs = json.load(open(f"{res}/overlays.json")) if os.path.exists(f"{res}/overlays.json") else []
    pts = [((c["start"] + c["end"]) / 2, c["text"]) for c in caps if not c.get("hidden")]
    pts += [((o["start"] + o["end"]) / 2, o["text"]) for o in ovs]
    pts.sort()
    de, dc = dur(exported), dur(check)
    rows = [f"# CapCut 실물 대조\n\n- 내보낸 영상 {de:.2f}초 / 확인본 {dc:.2f}초"
            + (" ← 길이 다름" if abs(de - dc) >= 0.2 else "") + "\n",
            "| 시각 | 자막·이모지 | " + " | ".join(BANDS) + " | 판정 |", "|---|---|" + "---|" * len(BANDS) + "---|"]
    tiles, bad = [], 0
    for t, label in pts:
        a, b = frame(exported, t), frame(check, t)
        if a is None or b is None:
            continue
        diffs = [float(np.abs(a[y0:y1].astype(int) - b[y0:y1].astype(int)).mean()) for y0, y1 in BANDS.values()]
        ng = any(d >= LIMIT for d in diffs)
        bad += ng
        rows.append(f"| {t:.2f} | {label} | " + " | ".join(f"{d:.0f}" for d in diffs) + f" | {'다름' if ng else '같음'} |")
        pair = np.hstack([a, b])
        pair = cv2.resize(pair, (540, 480))
        cv2.putText(pair, f"{t:.1f}s {'NG' if ng else ''}", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if ng else (0, 200, 0), 2)
        tiles.append(pair)
    for k in range(0, len(tiles), 6):
        grp = tiles[k:k + 6]
        while len(grp) < 6:
            grp.append(np.zeros_like(tiles[0]))
        cv2.imwrite(f"{out}/pairs_{k // 6:02d}.jpg", np.vstack([np.hstack(grp[:3]), np.hstack(grp[3:])]))
    rows.append(f"\n다름 {bad}곳 / {len(tiles)}곳")
    open(f"{out}/report.md", "w").write("\n".join(rows) + "\n")
    print(f"대조 {len(tiles)}곳, 다름 {bad}곳, 길이 {de:.2f} vs {dc:.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
