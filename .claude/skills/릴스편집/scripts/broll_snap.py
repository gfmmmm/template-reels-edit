#!/usr/bin/env python3
"""3단계 ③-A 화면 자료를 "이렇게·이런·이걸·여기·실제로" 같은 가리키는 말이 시작되는 순간에 붙인다(공용 규칙 61).
(한 생활용품 계정 게시본 대조: 스킬은 "이런 ○○에"에서 말하는 얼굴을 1초 넘게 보여 주다 문장 중간에
 시연으로 넘어갔다. 편집자는 "이런"과 함께 시연 — 시청자는 "이런 ○○"를 듣는 순간 그 물건을 보고 싶어 한다.
 운영자 계정 메뉴얼 3번 "화면녹화·실제 화면은 '이렇게', '실제로'가 시작되는 순간에 들어온다"도 같은 원리라 같이 쓴다)

사용법: broll_snap.py <결과폴더> [--all] [--max-late 0.2] [--max-early 2.5] (화면 계획(broll-plan.json) 다음, 카드 렌더 전에)
대상: 기본은 직접 찍은 시연 카드(component "Screen", role 없음).
 --all: 화면 녹화·모션그래픽 카드까지(인물 위 투명 카드·role 카드는 빼고). 모션그래픽은 시작을 당긴 만큼 장면 안 시간
 (at·…At·…End·beats)을 뒤로 밀어 장면 안 박자는 원래 시각 그대로 둔다 — 앞에 생긴 시간은 장면 첫 모습이 보인다.
규칙: 카드가 시작되는 문장 안에서, 카드 시작보다 --max-late 초 넘게 앞선 가리키는 말 중 카드에 가장 가까운 것(--max-early 초 안)의
 시작으로 카드 시작을 당긴다. 그 순간을 이미 다른 카드가 덮고 있거나 앞 카드와 겹치면 두지 않는다.
 가리키는 말이 없어도 AI가 제품 이름 문장에 붙이고 싶으면 카드에 "snap": true — 그 문장 첫 단어로 당긴다.
계정 메뉴얼 0번 "켜는 공용 기능"에 시연 시점이 켜져 있을 때만 쓴다(rebuild.sh --snap / --snap-all).
"""
import json
import os
import re
import sys

DEMO = ("이런", "이렇게", "이걸", "이거를", "요렇게", "여기다가", "여기에", "여기다", "여기서", "실제로")  # "이건"은 단정 문장("이건 진짜 사기")에 걸려 뺐다
OVERLAY_KINDS = {"PercentBar", "IconPairPop", "NumberPop", "CommentPop", "FaceScan", "HookPromptMini"}


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def shift_props(o, d, timeish=False):
    """장면 안 시간(장면 시작 기준 초)을 d 만큼 뒤로 — remap.py 와 같은 이름 규칙. 음수(-1 = 안 씀)는 그대로."""
    skip = ("a", "from", "clips", "rate", "in", "shots", "srcW", "srcH", "cropTop", "d", "speed", "scale", "pos")
    if isinstance(o, dict):
        for k, v in o.items():
            if k in skip:
                continue
            t = timeish or k == "beats" or k == "at" or k.endswith("At") or k.endswith("End")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if t and v >= 0:
                    o[k] = round(v + d, 3)
            else:
                shift_props(v, d, t)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if timeish and v >= 0:
                    o[i] = round(v + d, 3)
            else:
                shift_props(v, d, timeish)


def main(res):
    late, early, everything = arg("--max-late", 0.2), arg("--max-early", 2.5), "--all" in sys.argv
    tm = json.load(open(f"{res}/timemap.json"))
    words = json.load(open(f"{res}/편집본_단어시간.json"))
    plan = json.load(open(f"{res}/broll-plan.json"))
    clear = set()
    if os.path.exists(f"{res}/screens.json"):
        S = json.load(open(f"{res}/screens.json"))
        clear = {x["id"] for x in (S if isinstance(S, list) else S.get("screens", [])) if x.get("bg", "#000000") is None}
    span = {}
    for s in tm:
        a, b = span.get(s["take"], (1e9, -1))
        span[s["take"]] = (min(a, s["start"]), max(b, s["start"] + s["duration"]))
    cards = sorted(plan["cards"], key=lambda c: c["start"])
    fr = lambda t: round(round(t * 30) / 30, 4)  # noqa: E731
    moved = []
    for k, c in enumerate(cards):
        if c.get("role") or c.get("component") in OVERLAY_KINDS or c["id"] in clear:
            continue
        if c.get("component") != "Screen" and not everything:
            continue
        take = next((n for n, (a, b) in span.items() if a - 0.01 <= c["start"] < b), None)
        if take is None:
            continue
        a, b = span[take]
        if c.get("snap"):
            target = a
        else:
            cand = [w["s"] for w in words if w.get("take") == take and a - 0.01 <= w["s"] < c["start"] - late
                    and c["start"] - w["s"] <= early and re.sub(r"[^가-힣]", "", w["w"]).startswith(DEMO)]
            if not cand:
                continue
            target = max(cand)
        new = fr(target)
        if c["start"] - new <= late:
            continue
        prev_end = max((o["end"] for o in cards[:k] if o.get("component") not in OVERLAY_KINDS and o["id"] not in clear), default=0)
        if prev_end > new + 0.01:
            continue  # 앞 카드가 그 말을 이미 덮고 있다
        d = round(c["start"] - new, 3)
        if c.get("component") != "Screen":
            shift_props(c.get("props", {}), d)
        moved.append((c["id"], c["start"], new))
        c["start"] = new
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
    for cid, o, n in moved:
        print(f"{cid}: {o:.2f} → {n:.2f}")
    print(f"화면 자료 {len(moved)}개를 가리키는 말 시작으로 당김" + ("(모션그래픽은 장면 안 박자 그대로)" if everything else ""))


if __name__ == "__main__":
    main(sys.argv[1])
