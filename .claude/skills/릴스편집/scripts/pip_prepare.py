#!/usr/bin/env python3
"""3단계 ③-A 모션그래픽 장면의 인물 아래 창 준비 — 편집본(컷 미리보기)에서 그 구간을 잘라 원래 영상 + 오려낸 인물(투명)을 만든다.

사용법: pip_prepare.py <결과폴더> [Remotion폴더 — 기본은 환경.md 의 [Remotion폴더]]
입력: broll-plan.json에서 props.pip == true 인 카드(PromptScene·CommentScene)
출력: [Remotion폴더]/public/videos/pip_<id>.mp4, pip_<id>_cut.mov, 카드 props.pip를 파일 이름으로 바꿔 broll-plan.json 저장
오려내기: platform_util.person_matte — 맥은 Vision(person_matte.swift, 기기 안 처리), 그 외는 rembg. 도구가 없으면 오려내지 않고
 원래 화면 창만 쓰고 카드 props 에 "pip_matte": false 를 적는다. (윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.)
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def main(res, rem=None):
    rem = rem or pu.remotion_dir()
    plan = json.load(open(f"{res}/broll-plan.json"))
    src = f"{res}/preview/컷_미리보기.mp4"
    for c in plan["cards"]:
        p = c.get("props", {})
        if p.get("pip") is not True and not str(p.get("pip", "")).startswith("videos/pip_"):
            continue
        name = f"videos/pip_{c['id']}.mp4"
        out = f"{rem}/public/{name}"
        dur = c["end"] - c["start"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c['start']:.4f}", "-t", f"{dur + 0.1:.4f}", "-i", src,
                        "-c:v", "libx264", "-crf", "16", "-an", out], check=True)
        ok = pu.person_matte(out, out.replace(".mp4", "_cut.mov"))
        p["pip"] = name
        if not ok:
            p["pip_matte"] = False
        print(f"{c['id']}: 인물 창 {dur:.2f}초 → {name}" + ("" if ok else " (오려내기 없음)"))
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
