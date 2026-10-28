#!/usr/bin/env python3
"""3단계 ③-A 화면 계획 전 — 자료화면 후보 클립마다 처음·중간·끝 장면을 한 장으로 본다(공용 규칙 73).
(블라인드 시험: 물건을 들어 올려 밑(문제의 흔적)을 보여 주는 클립을 첫 장면만 보고 "거는 동작"으로 읽어 뺐다.
 그 문제를 말하는 자리에는 바닥 사진 확대가 들어가 말한 문제가 눈으로 증명되지 않았다 — 편집자는 그 클립을 썼다)

사용법: clip_sheet.py <결과폴더> <클립 또는 폴더> [...] → [결과폴더]/clip_sheets/<이름>.jpg (5장: 5·30·50·70·95%, 왼쪽부터 — 시각은 출력 줄에)
클립을 무엇으로 쓸지(문제 증거 / 사용 동작 / 결과) 정하기 전에 이 장을 보고 클립 목록에 "처음 → 끝에 무엇이 일어나는지" 한 줄로 적는다.
들어 올리기·뒤집기·열기처럼 "숨은 쪽을 보여 주는" 동작은 문제 증거 후보다.
"""
import os
import subprocess
import sys

VIDEO = (".mov", ".mp4", ".m4v")


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def main(res, paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(VIDEO))
        elif p.lower().endswith(VIDEO):
            files.append(p)
    out_dir = f"{res}/clip_sheets"
    os.makedirs(out_dir, exist_ok=True)
    for f in files:
        d = dur(f)
        if d <= 0:
            continue
        ts = [round(d * k, 2) for k in (0.05, 0.3, 0.5, 0.7, 0.95)]
        ins, fc = [], []
        for i, t in enumerate(ts):
            ins += ["-ss", f"{t:.2f}", "-i", f]
            fc.append(f"[{i}:v]scale=270:-2,pad=iw+6:ih:0:0:white[v{i}]")  # drawtext 가 없는 ffmpeg 도 있어 시각은 출력 줄에 적는다
        fc.append("".join(f"[v{i}]" for i in range(len(ts))) + f"hstack=inputs={len(ts)}[o]")
        out = f"{out_dir}/{os.path.splitext(os.path.basename(f))[0]}.jpg"
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[o]",
                            "-frames:v", "1", out])
        print(f"{os.path.basename(f)}\t{d:.1f}초\t장면 시각 {' · '.join(f'{t:.1f}' for t in ts)}\t{out if r.returncode == 0 else '실패'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
