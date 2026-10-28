#!/usr/bin/env python3
"""3단계 ③-B 자막 높이를 장면마다 — 인물 장면은 몸통·벽 쪽(얼굴 아래), 손·제품 장면은 기본 자리.
(한 생활용품 계정 게시본 대조: 편집자는 인물 장면에서 자막을 화면 높이 0.39~0.53으로 올려 손·제품을 가리지 않았고,
 손·제품 장면에서는 0.62~0.67에 두었다. 스킬은 늘 0.61에 고정해 인물 장면 자막이 손·제품을 덮었다)
계정 편집메뉴얼이 "자막 자리: 장면별"일 때만 쓴다. 말하는 얼굴만 나오는 계정(손·제품 없음)은 기본 자리 고정이 맞다.

사용법: caption_place.py <결과폴더> [--below 0.2] [--min 0.40] [--max 0.53]
입력: captions.json(captions.py 결과), timemap.json, broll-plan.json, zoom.json(focus = 디테일 확대 조각), faces.json·faces_found.json(face_anchor.py), preview/overlay_props.json 의 captionTop(기본 자리, px)
규칙: 자막 가운데 시각에 화면을 채운 것이 말하는 장면이고, 그 조각에서 얼굴을 찾았고, 디테일 확대가 아니면 인물 장면 →
 자막 가운데 높이 = 얼굴 높이 + --below(화면 비율), --min~--max 안. 그 밖은 기본 자리(dy 0).
출력: captions.json 자막마다 "dy"(px, +면 아래) — build_spec(CapCut)·확인본(overlay.tsx)이 같은 값을 쓴다.
"""
import json
import os
import sys


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def main(res):
    below, lo, hi = arg("--below", 0.2), arg("--min", 0.40), arg("--max", 0.53)
    man = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "편집메뉴얼.md")
    if "--force" not in sys.argv and not (os.path.exists(man) and "장면별" in open(man, encoding="utf-8").read()):
        print("편집메뉴얼 5번 자막 위치가 \"장면별\"이 아니다 — 고정 높이 계정이라 건너뜀(--force 로 강제)")
        return
    caps = json.load(open(f"{res}/captions.json"))
    tm = json.load(open(f"{res}/timemap.json"))
    cards = json.load(open(f"{res}/broll-plan.json")).get("cards", []) if os.path.exists(f"{res}/broll-plan.json") else []
    focus = json.load(open(f"{res}/zoom.json")).get("focus", {}) if os.path.exists(f"{res}/zoom.json") else {}
    faces = json.load(open(f"{res}/faces.json"))
    found = json.load(open(f"{res}/faces_found.json")) if os.path.exists(f"{res}/faces_found.json") else {}
    dy0 = float(open(f"{res}/caption_dy.txt").read()) if os.path.exists(f"{res}/caption_dy.txt") else 0.0
    base = 1120.0 + dy0  # build_spec 이 caption_dy 를 더하는 것과 같은 기준
    pp = f"{res}/preview/overlay_props.json"
    if os.path.exists(pp):
        base = float(json.load(open(pp)).get("captionTop", base))
    if os.path.exists(f"{res}/overlays.json") and any(o.get("kind") == "emoji" for o in json.load(open(f"{res}/overlays.json"))):
        print("⚠ 이모지가 자막 바로 아래에 붙는 계정이면 자막을 올린 곳의 이모지 y 도 같이 옮긴다")
    n = 0
    for c in caps:
        mid = (c["start"] + c["end"]) / 2
        c["dy"] = 0
        if any(x["start"] - 0.01 <= mid < x["end"] for x in cards):
            continue
        i = next((k for k, s in enumerate(tm) if s["start"] <= mid < s["start"] + s["duration"]), None)
        if i is None or not found.get(str(i)) or str(i) in focus:
            continue
        y = min(hi, max(lo, faces[str(i)][1] + below)) * 1920
        c["dy"] = int(round(y - base))
        n += 1
    json.dump(caps, open(f"{res}/captions.json", "w"), ensure_ascii=False, indent=1)
    print(f"자막 {len(caps)}개 중 인물 장면 {n}개를 얼굴 아래로 올림(기본 {base:.0f}px)")


if __name__ == "__main__":
    main(sys.argv[1])
