#!/usr/bin/env python3
"""CapCut 실화면 검수 — CapCut 플레이어를 실제로 처음부터 재생하며 0.5초마다 화면을 캡처한다.
확인본(Remotion으로 흉내 낸 자막 레이어)은 CapCut과 다르게 나올 수 있다(첫 편집: 제목 글꼴 빠짐·자막 줄바꿈·이모지 크기).
그래서 사용자에게 보여 주기 전에 반드시 CapCut이 실제로 그린 화면을 보고 확인본과 대조한다.

사용법: (opencv 있는 파이썬) capcut_screen_check.py <결과폴더> <영상 길이(초)>
전제: CapCut에서 그 프로젝트가 열려 있다(편집 화면). 맥 손쉬운 사용·화면 기록 권한.
동작: 창 위치 확인 → 플레이어 영역 찾기(가장 밝은 세로 9:16 직사각형) → 재생 중이면 멈춤 → 타임라인 맨 앞 클릭 → 재생 → 0.5초마다 캡처 → 멈춤
출력: [결과폴더]/capcut_screen/NNN.png, sheet.jpg(확인본과 위아래로 나란히 놓은 대조표)
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def editor_window():
    out = osa('tell application "System Events" to tell process "CapCut" to get {position, size} of every window')
    nums = [int(x) for x in out.replace(" ", "").split(",") if x.lstrip("-").isdigit()]
    n = len(nums) // 4
    wins = [(nums[2 * i], nums[2 * i + 1], nums[2 * n + 2 * i], nums[2 * n + 2 * i + 1]) for i in range(n)]
    return max(wins, key=lambda w: w[2] * w[3])  # 가장 큰 창 = 편집 화면


def find_player(img_path, win):
    """창 캡처에서 플레이어 영상 영역(세로 9:16)을 찾는다 — 위쪽 절반의 가운데 패널에서 어둡지 않은 열·행 범위."""
    import cv2
    import numpy as np
    im = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE).astype(int)
    H, W = im.shape
    sx = W / win[2]  # 레티나 배율
 # 편집 화면 가운데 칸(플레이어)만 본다: 가로 33~70%, 세로 5~65% (오른쪽 밝은 패널을 잡지 않게)
    ox, oy = int(W * 0.33), int(H * 0.05)
    mid = im[oy:int(H * 0.65), ox:int(W * 0.70)]
    cols = np.where((mid > 40).mean(axis=0) > 0.5)[0]
    best, cur = [], [cols[0]]
    for c in cols[1:]:
        if c == cur[-1] + 1:
            cur.append(c)
        else:
            best = max(best, cur, key=len); cur = [c]
    best = max(best, cur, key=len)
    x0, x1 = best[0], best[-1]
    rr = np.where((mid[:, x0:x1] > 30).mean(axis=1) > 0.9)[0]
    y0, y1 = rr.min(), rr.max()
    x0, x1, y0, y1 = x0 + ox, x1 + ox, y0 + oy, y1 + oy
    return (win[0] + x0 / sx, win[1] + y0 / sx, (x1 - x0) / sx, (y1 - y0) / sx)


def main(res, dur):
    out = f"{res}/capcut_screen"
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(f"{out}/{f}")
    osa('tell application "CapCut" to activate')
    time.sleep(1)
    win = editor_window()
    subprocess.run(["screencapture", "-x", "-R", ",".join(map(str, win)), f"{out}/_win.png"])
    px, py, pw, ph = find_player(f"{out}/_win.png", win)
    print("player", round(px), round(py), round(pw), round(ph))
 # 재생 중이면 멈춘다 (0.5초 간격 두 장이 다르면 재생 중)
    import cv2
    reg = f"{round(px)},{round(py)},{round(pw)},{round(ph)}"
    subprocess.run(["screencapture", "-x", "-R", reg, f"{out}/_a.png"]); time.sleep(0.5)
    subprocess.run(["screencapture", "-x", "-R", reg, f"{out}/_b.png"])
    if abs(cv2.imread(f"{out}/_a.png").astype(int) - cv2.imread(f"{out}/_b.png").astype(int)).mean() > 1.0:
        osa('tell application "System Events" to keystroke " "')
        time.sleep(0.8)
 # 타임라인 눈금자 맨 앞(창 왼쪽 + 150/1400 폭, 세로 584/809 높이 근처)을 눌러 0초로
    tx, ty = win[0] + win[2] * 150 / 1400, win[1] + win[3] * 584 / 809
    osa(f'tell application "System Events" to tell process "CapCut" to click at {{{round(tx)}, {round(ty)}}}')
    time.sleep(0.8)
    osa('tell application "System Events" to keystroke " "')  # 재생
    t0 = time.time()
    k = 0
    while time.time() - t0 < dur + 0.5:
        target = t0 + k * 0.5
        time.sleep(max(0, target - time.time()))
        subprocess.Popen(["screencapture", "-x", "-R", f"{round(px)},{round(py)},{round(pw)},{round(ph)}", f"{out}/{k:03d}.png"])
        k += 1
    osa('tell application "System Events" to keystroke " "')  # 멈춤
    time.sleep(1)
    print("frames", k)


if __name__ == "__main__":
    if pu.os_kind() != "mac":
        print("이 기능은 맥에서만 됩니다. CapCut 화면을 직접 확인해 주세요.")
        sys.exit(2)
    main(sys.argv[1], float(sys.argv[2]))
