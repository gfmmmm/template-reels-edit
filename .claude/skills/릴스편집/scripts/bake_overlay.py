#!/usr/bin/env python3
"""인물 위에 얹는 투명 카드를 인물 영상에 미리 구워 넣는다(불투명 클립으로 바꾼다).

왜: CapCut은 투명 ProRes의 반투명 픽셀(번짐·빛·그림자·흐린 가장자리)을 거의 불투명하게 그린다.
 얼굴 스캔의 은은한 빛이 CapCut에서 흰 덩어리로 뭉개졌다(IMG_0517).
 확인본(ffmpeg 합성)은 멀쩡해서 승인본과 실물이 달라진다.
언제: 인물 위에 얹는 투명 카드(component가 인물을 덮지 않고 비쳐 보이는 것 — FaceScan, PercentBar, IconPop 등)에
 반투명 효과가 있을 때. 배경이 꽉 찬 장면(PromptScene·ReportScene 등)은 필요 없다.
사용법: bake_overlay.py <결과폴더> <카드 id> <편집용 영상>
 - 원래 투명 카드는 cards/<id>_alpha.mov로 옮기고, cards/<id>.mov를 구운 불투명 클립(ProRes 422 HQ)으로 바꾼다.
 다시 돌리면 _alpha를 원본으로 쓴다. build_spec·render_check는 그대로 cards/<id>.mov를 쓴다.
 - 인물은 컷편집 그대로(배속 포함) 원본 해상도로 다시 뽑아 쓴다(preview/인물_원본해상도.mp4, 한 번 만들면 재사용).
 - 그 구간 인물 조각은 확대 1.0이어야 한다(구운 클립엔 CapCut 확대가 안 걸린다 — zoom.json에서 빼 둔다).
 - 이미 CapCut에 조립한 뒤라면 프로젝트 assets/video/의 같은 카드 파일을 이 클립으로 바꾼다(CapCut 끈 상태에서).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(res, cid, video):
    card = next(c for c in json.load(open(f"{res}/broll-plan.json"))["cards"] if c["id"] == cid)
    alpha = f"{res}/cards/{cid}_alpha.mov"
    if not os.path.exists(alpha):
        shutil.move(f"{res}/cards/{cid}.mov", alpha)
    person = f"{res}/preview/인물_원본해상도.mp4"
    if not os.path.exists(person) or os.path.getmtime(person) < os.path.getmtime(f"{res}/timemap.json"):
        subprocess.run([sys.executable, f"{HERE}/render_cut.py", res, video, person, "--scale", "1"], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", alpha],
                               capture_output=True, text=True).stdout)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{card['start']:.4f}", "-t", f"{dur:.4f}", "-i", person, "-i", alpha,
                    "-filter_complex", "[0:v]setpts=PTS-STARTPTS,fps=30,scale=1080:1920,format=yuva444p12le[b];"
                    "[b][1:v]overlay=format=auto,format=yuv422p10le[v]",
                    "-map", "[v]", "-an", "-t", f"{dur:.4f}", "-c:v", "prores_ks", "-profile:v", "3", f"{res}/cards/{cid}.mov"], check=True)
    print(f"구움: cards/{cid}.mov ({dur:.3f}초, 원래 투명 카드 → cards/{cid}_alpha.mov)")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
