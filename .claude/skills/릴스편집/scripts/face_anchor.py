#!/usr/bin/env python3
"""3단계 ③-B 확대 기준점 — 조각마다 얼굴 가운데를 찾아 faces.json에 적는다.

사용법: face_anchor.py <결과폴더>
입력: timemap.json, preview/컷_미리보기.mp4(2단계 기준 미리보기, 1080×1920)
출력: faces.json {"조각번호(0부터)": [fx, fy]} (0~1, 화면 왼쪽 위 기준)
왜: 화면 가운데를 기준으로 확대하면 얼굴이 가운데가 아닐 때 얼굴이 대각선으로 밀려 보인다.
 build_spec.py(CapCut 위치 키프레임)와 render_check.py(확인본)가 이 점을 기준으로 확대한다.
얼굴 인식: platform_util.face_centers — 맥은 Vision(face_center.swift, 기기 안 처리), 그 외는 opencv(없으면 화면 가운데). 얼굴이 안 잡힌 조각은 앞 조각 값을 쓴다.
(윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.)
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def main(res):
    segs = json.load(open(f"{res}/timemap.json"))
    prev = f"{res}/preview/컷_미리보기.mp4"
    tmp = tempfile.mkdtemp()
    paths = []
    for i, s in enumerate(segs):
        p = f"{tmp}/{i:03d}.jpg"
        t = s["start"] + s["duration"] / 2
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", prev, "-frames:v", "1", "-vf", "scale=540:-2", p], check=True)
        paths.append(p)
    out = pu.face_centers(paths)
    faces, last = {}, [0.5, 0.4]
    for i, f in enumerate(out):
        if f is not None:
            last = f
        faces[str(i)] = last
    json.dump(faces, open(f"{res}/faces.json", "w"), indent=1)
 # 얼굴을 실제로 찾은 조각(앞 조각 값을 빌려 쓴 조각과 구별) — caption_place.py 가 인물 장면을 가를 때 쓴다
    json.dump({str(i): f is not None for i, f in enumerate(out)}, open(f"{res}/faces_found.json", "w"))
    miss = sum(1 for f in out if f is None)
    print(f"얼굴 기준점 {len(faces)}개 (못 찾은 조각 {miss}개는 앞 조각 값) → faces.json")


if __name__ == "__main__":
    main(sys.argv[1])
