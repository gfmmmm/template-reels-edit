#!/usr/bin/env python3
"""③-E 자막 크기 전수 대조 — CapCut 실물과 승인본(확인본)에서 자막·이모지·라벨·메모마다 글자 가로 범위를 재서 비교.

사용법: text_size_check.py <결과폴더> <CapCut 내보낸 영상> <승인본 영상> [--tol 25]
자막마다 시작+0.25초(짧으면 가운데), 오버레이는 가운데 시각에서 세로 950~1570px 띠의 흰·노랑·빨강 글자 x 범위.
좌우 끝이 tol(px) 넘게 다르거나 한쪽에만 글자가 있으면 표시. 종료 코드 1 = 다른 곳 있음.
(자막 크기를 몇 곳만 재고 통과시켰다가 사용자가 다른 장면 크기 차이를 지적 → 전수로)
사용자가 "이대로 둔다"고 한 차이는 <결과폴더>/크기예외.txt 에 글자를 한 줄씩 적으면 검사에서 뺀다(예: 2탄도).
"""
import json
import subprocess
import sys


def frame(p, t, y0=950, h=620):
 # 재는 띠 바깥은 검정으로 칠해 box가 띠 안 글자만 보게 한다
    return subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", p, "-frames:v", "1", "-vf",
                           f"crop=1080:620:0:950,drawbox=x=0:y=0:w=1080:h={y0 - 950}:color=black:t=fill,drawbox=x=0:y={y0 - 950 + h}:w=1080:h=620:color=black:t=fill",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout


def box(raw):
    xs = []
    for y in range(0, 620, 2):
        for x in range(0, 1080, 3):
            i = (y * 1080 + x) * 3
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            if (r > 235 and g > 235 and b > 235) or (r > 200 and g > 160 and b < 90) or (r > 200 and g < 60 and b < 60):
                xs.append(x)
    return (min(xs), max(xs)) if xs else None


def main(res, exp, ref, tol=25):
    caps = [c for c in json.load(open(f"{res}/captions.json")) if not c.get("hidden")]
    ov = json.load(open(f"{res}/overlays.json"))
    items = [(c["start"] + min(0.25, (c["end"] - c["start"]) / 2), c["text"]) for c in caps] + [((o["start"] + o["end"]) / 2, o["text"]) for o in ov]
    import os
    allow = set(open(f"{res}/크기예외.txt").read().split("\n")) - {""} if os.path.exists(f"{res}/크기예외.txt") else set()
    items = [x for x in items if x[1] not in allow]
 # 퍼센트 막대(흰 카드, 세로 약 1,190~1,400px)가 떠 있는 동안은 막대를 자막으로 잘못 재지 않게 자막 띠(1,060~1,180px)만 잰다(한 편집 사례)
    bars = []
    if os.path.exists(f"{res}/broll-plan.json"):
        bars = [(c["start"], c["end"]) for c in json.load(open(f"{res}/broll-plan.json"))["cards"] if c["component"] == "PercentBar"]
    bad = []
    for t, tx in sorted(items):
        on_bar = any(a0 <= t < a1 for a0, a1 in bars)
        if on_bar and tx in {o["text"] for o in ov}:
            continue  # 막대와 같은 자리 이모지는 넣지 않는다(규칙) — 남아 있어도 막대에 가려 잴 수 없다
        y0, h = (1060, 120) if on_bar else (950, 620)
        a, b = box(frame(exp, t, y0, h)), box(frame(ref, t, y0, h))
        if (a and b and (abs(a[0] - b[0]) > tol or abs(a[1] - b[1]) > tol)) or bool(a) != bool(b):
            bad.append((round(t, 2), tx, a, b))
    print(f"검사 {len(items)}개, 다름 {len(bad)}개")
    for x in bad:
        print(x)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    tol = int(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 25
    main(*sys.argv[1:4], tol)
