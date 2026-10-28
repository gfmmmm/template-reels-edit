#!/usr/bin/env python3
"""1단계 정답지 보정 — 게시본의 말이 원본보다 몇 배 빠른지 문장마다 잰다(소리 무늬 정렬, DTW).
(한 생활용품 계정: Premiere 프로젝트만 읽고 "말은 1.0배"로 적었는데, 게시본을 원본과 맞대 보니 9문장이 1.1배(음 높이 유지),
 바닥 구간 3문장만 1.0배였다. 스킬은 1.0배로 편집해 게시본보다 2초 늘어졌다. 프로젝트 파일 배속 값은 중첩 시퀀스·내보내기에서
 걸린 배속을 놓칠 수 있다 — 같은 원본의 게시본이 있으면 이걸로 확인한다)

사용법: speed_match.py <결과폴더> <게시본.mp4> [--audio <편집용 말 영상>]
입력: <결과폴더>/takes.json · stt_chunks/chunks.json (2단계 ①② 결과 — 원본 쪽 문장 위치), 게시본(받아써서 같은 문장 위치를 찾는다)
출력: 문장마다 "원본 길이 ÷ 게시본 길이"(1.10 = 1.1배)와 0.3초 구간별 값. 구간별 값이 고르면 배속, 한 곳만 튀면 그 자리를 자른 것.
 결과는 편집메뉴얼(0번 표가 있으면 "말 배속", 없으면 3번)과 13번 cutplan 값에 (게시본) 표시로 적는다.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SR, HOP, NF = 16000, 160, 512


def pcm(path, a=None, b=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error"] + (["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}"] if a is not None else []) + \
          ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.int16).astype(float) / 32768


def feat(x):
    edges = np.geomspace(80, 6000, 41)
    f = np.fft.rfftfreq(NF, 1 / SR)
    bins = [(f >= edges[i]) & (f < edges[i + 1]) for i in range(40)]
    fr = np.array([x[i:i + NF] * np.hanning(NF) for i in range(0, len(x) - NF, HOP)])
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    M = np.log(np.array([S[:, b].sum(1) for b in bins]).T + 1e-8)
    M = M - M.mean(0)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    return M, 10 * np.log10(S.sum(1) + 1e-12)


def dtw(a, b):
    n, m = len(a), len(b)
    C = 1 - a @ b.T
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        c = int(i * m / n)
        for j in range(max(1, c - 150), min(m, c + 150) + 1):
            D[i, j] = C[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = int(np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]]))
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    return path[::-1]


def norm(t):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", t or "")


def main(res, posted):
    audio = sys.argv[sys.argv.index("--audio") + 1] if "--audio" in sys.argv else json.load(open(f"{res}/spec.json")).get("video")
    takes = json.load(open(f"{res}/takes.json"))
    chunks = json.load(open(f"{res}/stt_chunks/chunks.json"))
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", posted, "-vn", "-ac", "1", "-ar", str(SR), wav])
    r = pu.transcribe(wav)
    os.unlink(wav)
    PW = [(norm(w["word"]), w["start"], w["end"]) for s in r["segments"] for w in s["words"] if norm(w["word"])]
    A = pcm(posted)
    pos = 0
    print("| 문장 | 원본 길이 | 게시본 길이 | 배 | 0.3초 구간별 |\n|---|---|---|---|---|")
    for tk in takes:
        W = chunks[tk[2]]["words"] if 0 <= tk[2] < len(chunks) else []
        if not W:
            continue
        rng = tk[3] if len(tk) > 3 else [0, len(W) - 1]  # 단어 범위가 없으면 덩어리 전체
        w0, w1 = W[rng[0]], W[rng[1]]
        f0, f1 = norm(w0["w"])[:2], norm(w1["w"])[-2:]
        i = next((k for k in range(pos, len(PW)) if PW[k][0].startswith(f0)), None)
        if i is None:
            print(f"| {tk[1][:18]} | — | 게시본에 없음 | — | |")
            continue
        n_w = rng[1] - rng[0]
        j = next((k for k in range(i + max(0, n_w - 2), min(len(PW), i + n_w + 4)) if PW[k][0].endswith(f1)), i + n_w)
        j = min(j, len(PW) - 1)
        pos = j + 1
        a0, a1 = max(0.0, PW[i][1] - 0.05), PW[j][2] + 0.05
        s0, s1 = max(0.0, w0["s"] - 0.1), w1["e"] + 0.1
        fa, ea = feat(A[int(a0 * SR):int(a1 * SR)])
        fs, _ = feat(pcm(audio, s0, s1))
        if len(fa) < 20 or len(fs) < 20:
            continue
        p = dtw(fa, fs)
        ai, sj = np.array([x for x, _ in p]), np.array([y for _, y in p])
        k = np.where(ea[ai] > np.percentile(ea, 40))[0]
        k = k[int(len(k) * 0.1):int(len(k) * 0.9)]
        x, y = ai[k] * 0.01, sj[k] * 0.01
        if len(x) < 10:
            continue
        sl = np.polyfit(x, y, 1)[0]
        loc = []
        for t in np.arange(x.min(), x.max() - 0.3, 0.3):
            m = (x >= t) & (x < t + 0.3)
            if m.sum() > 5:
                loc.append(round(float(np.polyfit(x[m], y[m], 1)[0]), 2))
        print(f"| {tk[1][:18]} | {s1 - s0:.2f} | {a1 - a0:.2f} | **{sl:.2f}** | {' / '.join(map(str, loc))} |")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
