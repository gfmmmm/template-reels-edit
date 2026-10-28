#!/usr/bin/env python3
"""3단계 장면 점검 — 끼인 장면(번쩍임)과 첫 화면 가장자리의 잘린 얼굴을 찾는다(공용 규칙 72).
(블라인드 시험: v3 는 자료화면 두 장 사이에 말하는 장면 0.33초가 끼어 얼굴 윗부분이 번쩍였고,
 블라인드 편집은 첫 5프레임 동안 화면 오른쪽 위에 잘린 얼굴 반쪽이 지나갔다. 둘 다 계정과 상관없이 어색하다)

사용법: scene_check.py <결과폴더> [--min 0.5] [--fix] (확인본을 만든 뒤 — rebuild.sh 가 매번 부른다)
본다:
 1. 끼인 장면 — 자료화면 카드 끝과 다음 카드 시작 사이에 드러나는 말하는 장면이 --min 초보다 짧으면. 인물 위 투명 카드는 장면으로 치지 않는다.
 --fix: 앞 카드가 직접 찍은 시연 카드(component "Screen")면 앞 카드 끝을 다음 카드 시작까지 늘린다 → rebuild.sh 로 카드를 다시 만든다.
 모션그래픽 카드면 목록만(③-A 7 다시 렌더).
 2. 첫 화면 잘린 얼굴 — 확인본 0.03·0.15·0.3초 장면에서 얼굴이 화면 가장자리(가로 12%·88% 바깥, 위 8% 안)에 걸려 있으면.
 고치는 법: 첫 조각 시작을 인물이 빠진 뒤로 늦추거나(edge_fix), 첫 장면 확대 기준점(zoom.json focus)을 반대쪽으로.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

OVERLAY_KINDS = {"PercentBar", "IconPairPop", "NumberPop", "CommentPop", "FaceScan", "HookPromptMini"}


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def main(res):
    mn, fixing = arg("--min", 0.5), "--fix" in sys.argv
    plan = json.load(open(f"{res}/broll-plan.json")) if os.path.exists(f"{res}/broll-plan.json") else {"cards": []}
    clear = set()
    if os.path.exists(f"{res}/screens.json"):
        S = json.load(open(f"{res}/screens.json"))
        clear = {x["id"] for x in (S if isinstance(S, list) else S.get("screens", [])) if x.get("bg", "#000000") is None}
    cards = sorted([c for c in plan["cards"] if c.get("component") not in OVERLAY_KINDS and c["id"] not in clear],
                   key=lambda c: c["start"])
    found = 0
    changed = False
    for p, q in zip(cards, cards[1:]):
        gap = q["start"] - p["end"]
        if 0.02 < gap < mn and not any(o["start"] < q["start"] - 0.01 and o["end"] > p["end"] + 0.01 for o in cards if o not in (p, q)):
            found += 1
            msg = f"⚠ 끼인 장면 {p['end']:.2f}~{q['start']:.2f}초 ({gap:.2f}초) — {p['id']} 와 {q['id']} 사이에 말하는 장면이 잠깐 비친다"
            if fixing and p.get("component") == "Screen":
                p["end"] = q["start"]
                changed = True
                msg += f" → {p['id']} 끝을 {q['start']:.2f}초로 늘림"
            else:
                msg += " — 앞 카드를 늘리거나 뒤 카드를 당긴다"
            print(msg)
    if changed:
        json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
        print("broll-plan.json 고침 → rebuild.sh 로 카드·확인본을 다시 만든다")
    prev = next((f"{res}/preview/{n}" for n in ("확인본.mp4", "최종본_고화질.mp4", "컷_미리보기.mp4")
                 if os.path.exists(f"{res}/preview/{n}")), None)
    if prev:
        tmp = tempfile.mkdtemp()
        shots = []
        for k, t in enumerate((0.03, 0.15, 0.3)):
            out = f"{tmp}/{k}.jpg"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", prev, "-frames:v", "1",
                            "-vf", "scale=540:-2", out], check=True)
            shots.append(out)
        edge = []
        for t, c in zip((0.03, 0.15, 0.3), pu.face_centers(shots)):
            if c and (c[0] < 0.12 or c[0] > 0.88 or c[1] < 0.08):
                edge.append(f"{t:.2f}초 ({c[0]:.2f}, {c[1]:.2f})")
        if edge:
            found += 1
            print("⚠ 첫 화면 가장자리에 잘린 얼굴: " + ", ".join(edge) + " — 첫 조각 시작을 늦추거나 확대 기준점을 옮긴다")
    print(f"장면 점검 {found}곳")


if __name__ == "__main__":
    main(sys.argv[1])
