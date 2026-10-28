#!/usr/bin/env python3
"""손떨림 재기 — 손으로 든 장면만 골라 preprocess.sh --deshake 를 켠다(정답지: 편집자가 손으로 든 장면 2곳에만 흔들림 안정화).

사용법: shake_check.py <영상> [영상 ...] [--fps 10]
하는 일: 줄인 흑백 프레임(폭 360)끼리 위상 상관(소수점 보간)으로 프레임마다 화면 이동을 재고, 0.5초 이동 평균(의도한 움직임)을 뺀 떨림 크기를 낸다.
기준(1080 폭 환산 px, 0.5초보다 빠른 떨림만): 2 미만 "적음" · 2~4 "보통" · 4 이상 "큼 → 보정 권장". 천천히 옮기는 팬·걸어가기는 떨림으로 세지 않는다.
"""
import re
import subprocess
import sys

import numpy as np


def frames(path, fps, w=160):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    nums = [int(float(x)) for x in re.findall(r"-?\d+(?:\.\d+)?", out)]
    W, H = nums[0], nums[1]
    if any(abs(n) % 180 == 90 for n in nums[2:]):
        W, H = H, W  # 아이폰 세로 영상: ffmpeg 가 세워서 준다
    h = int(round(w * H / W / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    k = len(raw) // (w * h)
    return np.frombuffer(raw[:k * w * h], np.uint8).reshape(k, h, w).astype(float), w


def shift(a, b):
    """a 가 b 보다 얼마나 옮겨졌나(px, 소수점까지 — 봉우리 주변 포물선 보간)."""
    A, B = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-9
    r = np.fft.ifft2(R).real
    y, x = np.unravel_index(np.argmax(r), r.shape)

    def sub(v_m, v_0, v_p):
        den = v_m - 2 * v_0 + v_p
        return 0.0 if den == 0 else 0.5 * (v_m - v_p) / den
    dy = sub(r[(y - 1) % r.shape[0], x], r[y, x], r[(y + 1) % r.shape[0], x])
    dx = sub(r[y, (x - 1) % r.shape[1]], r[y, x], r[y, (x + 1) % r.shape[1]])
    y, x = y + dy, x + dx
    if y > r.shape[0] / 2:
        y -= r.shape[0]
    if x > r.shape[1] / 2:
        x -= r.shape[1]
    return x, y


def trajectory(path, fps=30.0, w=360):
    F, w = frames(path, fps, w)
    d = np.array([shift(F[i + 1], F[i]) for i in range(len(F) - 1)], float)
    return np.vstack([[0, 0], np.cumsum(d, axis=0)]), w


def smooth_path(pos, k):
    k = max(3, int(k)) | 1
    pad = np.pad(pos, ((k // 2, k // 2), (0, 0)), mode="edge")  # 끝을 0으로 채우면 앞뒤에서 떨림이 크게 잡힌다(예전 버그)
    return np.vstack([np.convolve(pad[:, j], np.ones(k) / k, mode="valid") for j in range(2)]).T


def main():
    fps = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30.0
    skip = {sys.argv.index("--fps") + 1} if "--fps" in sys.argv else set()
    paths = [p for i, p in enumerate(sys.argv[1:], 1) if not p.startswith("--") and i not in skip]
    for p in paths:
        pos, w = trajectory(p, fps)
        if len(pos) < 6:
            print(f"{p}: 너무 짧음")
            continue
        res = pos - smooth_path(pos, fps / 2)  # 0.5초보다 빠른 흔들림만
        jitter = float(np.sqrt((res ** 2).sum(axis=1)).mean()) * (1080 / w)
        tag = "큼 → 보정 권장" if jitter >= 4 else "보통" if jitter >= 2 else "적음"
        print(f"{p.split('/')[-1]}\t떨림 {jitter:.1f}px\t{tag}")

if __name__ == "__main__":
    main()
