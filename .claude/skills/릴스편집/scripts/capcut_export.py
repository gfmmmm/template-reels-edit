#!/usr/bin/env python3
"""CapCut 자동 내보내기 (영어판 CapCut 9.x, macOS) — 실험으로 확인한 방법.

사용법: capcut_export.py [--timeout 600]
전제: 사용자가 손을 뗀 상태(마우스·키보드를 움직이면 클릭이 엇나간다) + 내보낼 프로젝트가 CapCut 편집 화면에 열려 있음.
 (홈 화면에서 프로젝트를 여는 단계는 아직 자동화 못 함 — capcut-cli export --batch의 "파일 열기"는 CapCut이 거부.)
방법:
 1. 메뉴줄 File → Export는 이름으로 누른다(System Events). 한국어판은 메뉴 이름이 달라 안 됨 → 영어판 필요.
 2. 내보내기 창(sheet)은 접근성으로 일부 읽힌다: 'Export to' 값 = 이번 출력 폴더(<위치>/<이름>), 버튼 위치·크기.
 단 AXPress로는 눌리지 않는다 → 버튼 위치·크기를 읽어 가운데에 진짜 마우스 클릭(CGEvent, mouse_click.swift).
 3. <출력 폴더>/<폴더 이름>.mov 가 생기고 크기가 3번 연속 같으면 끝. 완료 창(Share/Close)은 Close 버튼 진짜 클릭으로 닫는다.
출력: 내보낸 파일 경로 한 줄(실패하면 이유와 함께 종료 코드 1).
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLICK = os.path.expanduser("~/.cache/reels-edit/mouse_click")


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def click(x, y):
    src = f"{SKILL}/scripts/mouse_click.swift"
    if not os.path.exists(CLICK) or os.path.getmtime(CLICK) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(CLICK), exist_ok=True)
        subprocess.run(["swiftc", "-O", src, "-o", CLICK], check=True)
    subprocess.run([CLICK, str(int(x)), str(int(y))], check=True)


SHEET = 'sheet 1 of window "CapCut"'


def buttons():
    """내보내기 창 버튼들 [(x, y, w, h)] — 위치·크기를 접근성으로 읽는다(설명 이름은 비어 있을 때가 많다)."""
    out, rc = osa(f'tell application "System Events" to tell process "CapCut" to get {{position, size}} of every button of {SHEET}')
    if rc:
        return []
    n = [int(v) for v in out.replace(" ", "").split(",") if v.lstrip("-").isdigit()]
    half = len(n) // 2
    return [(n[i], n[i + 1], n[half + i], n[half + i + 1]) for i in range(0, half, 2)]


def out_folder():
    """'Export to' 칸 값 = 이번 내보내기 폴더(<저장 위치>/<이름>). 파일은 그 안의 <이름>.mov."""
    out, _ = osa(f'tell application "System Events" to tell process "CapCut" to get value of every static text of {SHEET}')
    for v in out.split(", "):
        if v.startswith("/"):
            return v.strip()
    return None


def main():
    timeout = float(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 600
    if pu.os_kind() != "mac":
        print("이 기능은 맥에서만 됩니다. CapCut에서 직접 내보내 주세요.")
        sys.exit(2)
    if not pu.capcut_running():
        sys.exit("CapCut이 꺼져 있다 — 프로젝트를 열어 둔 상태에서 실행.")
    osa('tell application "CapCut" to activate')
    time.sleep(0.8)
    _, rc = osa('tell application "System Events" to tell process "CapCut" to click menu item "Export" of menu "File" of menu bar 1')
    if rc:
        sys.exit("File → Export 메뉴를 못 눌렀다(한국어판이거나 편집 화면이 아님).")
    for _ in range(20):
        time.sleep(0.5)
        folder = out_folder()
        bs = [b for b in buttons() if b[2] > 50]
        if folder and len(bs) >= 2:
            break
    else:
        sys.exit("내보내기 창이 안 떴다.")
    ok = max(bs, key=lambda b: b[0])  # 아래 오른쪽 = Export
    target = os.path.join(folder, os.path.basename(folder) + ".mov")
    before = os.path.getmtime(target) if os.path.exists(target) else 0
    x, y, w, h = ok
    click(x + w / 2, y + h / 2)
    t0, last, same = time.time(), -1, 0
    while time.time() - t0 < timeout:
        time.sleep(2)
        if os.path.exists(target) and os.path.getmtime(target) > before:
            sz = os.path.getsize(target)
            same = same + 1 if sz == last else 0
            last = sz
            if same >= 3:
                break
    else:
        sys.exit(f"시간 초과: {target}")
 # 완료 창 닫기: 버튼 셋 중 가운데(Close) — 위치는 매번 읽는다
    time.sleep(1)
    btns = sorted([b for b in buttons() if b[2] > 50], key=lambda b: b[0])
    if len(btns) >= 2:  # 완료 창: ... Close, Share → 오른쪽에서 두 번째
        bx, by, bw, bh = btns[-2]
        click(bx + bw / 2, by + bh / 2)
    print(target)


if __name__ == "__main__":
    main()
