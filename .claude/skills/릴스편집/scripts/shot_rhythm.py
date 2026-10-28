#!/usr/bin/env python3
"""3단계 장면 리듬 검사 — 화면에 같은 그림이 얼마나 오래 머무는지 편집 설계(timemap·broll-plan·zoom)로 잰다.
(한 생활용품 계정 시험: 규칙대로 다 넣었는데도 편집자 게시본보다 늘어져 보였다. 장면 하나 가운데 값이
 게시본 1.2초 ↔ 스킬 1.6초, 2초 넘는 장면 3곳 ↔ 5곳. 같은 그림이 2초 넘게 머무르는 곳이 "늘어짐"의 정체였다)

사용법: shot_rhythm.py <결과폴더> --max <계정 메뉴얼 12번 "장면 리듬" 상한> [--fix] (--max 가 없으면 건너뛴다 — 공용 58 은 메뉴얼이 켤 때만)
세는 것: 말하는 장면과 직접 찍은 시연 카드(component "Screen"). 모션그래픽·화면 기록 장면은 장면 안 박자로 바뀌어 세지 않고,
인물 위 투명 카드(PercentBar 등, bg null)는 장면으로 치지 않는다(충돌 점검: 운영자 영상에서 9~14곳 오탐)
--fix: 상한을 넘는 직접 찍은 시연 카드(component "Screen", role 없음, 멈춘 사진 아님)를 가운데에서 둘로 나눈다 —
 뒤 카드는 같은 클립의 다음 순간(앞 카드 길이 + 0.3초 뒤부터)을 1.3배 확대(공용 규칙 58 ③). 말하는 장면이 넘으면 목록만
 (그 자리에 다른 각도 시연이나 디테일 확대를 AI가 고른다). 나눈 뒤 screen_clip.py 로 카드를 만든다.
장면이 바뀌는 때: 말하는 장면 원본이 이어지지 않는 곳(점프컷·다른 파일), 확대 배율이 바뀌는 곳, 자료화면 카드 시작·끝.
J컷 카드(role jcut)는 앞 장면을 이어 보여 주므로 시작은 장면 바뀜이 아니다(J컷 0~2.2초가 한 화면인데 둘로 셌다).
출력: 장면 수·가운데 값, --max 를 넘는 장면 목록(마지막 장면은 끝 문구 자리라 뺌). 넘는 장면은 3_효과 "장면 리듬"대로 둘로 나눈다.
"""
import json
import os
import statistics
import subprocess
import sys


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def split(res, mx):
    plan = json.load(open(f"{res}/broll-plan.json"))
    S = json.load(open(f"{res}/screens.json"))
    L = S if isinstance(S, list) else S["screens"]
    scr = {x["id"]: x for x in L}
    out = []
    for c in list(plan["cards"]):
        d = c["end"] - c["start"]
        sc = scr.get(c["id"])
        if d <= mx or c.get("component") != "Screen" or c.get("role") or not sc or not sc.get("layers"):
            continue
        ly = sc["layers"][0]
        if ly.get("freeze") or "in" not in ly:
            continue
        cut = round(round((c["start"] + d / 2) * 30) / 30, 4)
        c2 = dict(c, id=c["id"] + "b", start=cut, reason=(c.get("reason", "") + " — 장면 2초 넘어 둘로(다음 순간 + 확대)"))
        c["end"] = cut
        s2 = json.loads(json.dumps(sc))
        s2["id"] = c2["id"]
        l2 = s2["layers"][0]
        l2["in"] = round(ly["in"] + (cut - c["start"]) * ly.get("speed", 1.0) + 0.3, 3)
        try:  # 클립이 모자라면 같은 순간을 확대만
            src_len = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                            ly["src"]], capture_output=True, text=True).stdout.strip())
            if l2["in"] + (c2["end"] - cut) * l2.get("speed", 1.0) > src_len - 0.05:
                l2["in"] = round(ly["in"] + (cut - c["start"]) * ly.get("speed", 1.0), 3)
        except ValueError:
            pass
        k = [round(v * 1.3, 3) for v in ly.get("scale", [1.0, 1.0])]
        l2["scale"] = k
        sc["end"], s2["start"], s2["end"] = round(cut - c["start"], 4), 0, round(c2["end"] - cut, 4)
        plan["cards"].insert(plan["cards"].index(c) + 1, c2)
        L.insert(L.index(sc) + 1, s2)
        out.append(c["id"])
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
    json.dump(S, open(f"{res}/screens.json", "w"), ensure_ascii=False, indent=1)
    if out:
        print("둘로 나눈 시연 카드:", ", ".join(out))


# 인물 위에 얹는 투명 카드 — 그 아래 말 장면 컷이 그대로 보인다(장면으로 세지 않는다)
OVERLAY_KINDS = {"PercentBar", "IconPairPop", "NumberPop", "CommentPop", "FaceScan", "HookPromptMini"}


def main(res):
    if "--max" not in sys.argv:
        print("장면 리듬 상한(--max)이 없다 — 계정 메뉴얼 12번에 \"장면 리듬\" 값이 있을 때만 검사한다(공용 58). 건너뜀")
        return
    mx = arg("--max", 2.0)
    if "--fix" in sys.argv and os.path.exists(f"{res}/screens.json"):
        split(res, mx)
    tm = json.load(open(f"{res}/timemap.json"))
    try:
        z = json.load(open(f"{res}/zoom.json")).get("scales", {})
    except FileNotFoundError:
        z = {}
    try:
        cards = json.load(open(f"{res}/broll-plan.json")).get("cards", [])
    except FileNotFoundError:
        cards = []
    clear = set()
    if os.path.exists(f"{res}/screens.json"):
        S = json.load(open(f"{res}/screens.json"))
        clear = {x["id"] for x in (S if isinstance(S, list) else S.get("screens", [])) if x.get("bg", "#000000") is None}
    cards = [c for c in cards if c.get("component") not in OVERLAY_KINDS and c["id"] not in clear]
    end = tm[-1]["start"] + tm[-1]["duration"]
    cuts = {0.0, round(end, 3)}
    for i, s in enumerate(tm[1:], 1):
        p = tm[i - 1]
        jump = abs(s["src_in"] - p["src_out"]) > 0.05
        if jump or float(z.get(str(i), 1.0)) != float(z.get(str(i - 1), 1.0)):
            cuts.add(round(s["start"], 3))
    spans = [(c["start"], c["end"], c["id"], c.get("component")) for c in cards if c["end"] - c["start"] > 0.05]
    jc = {c["id"] for c in cards if c.get("role") == "jcut"}
    for a, b, cid, _ in spans:
        if cid in jc:  # J컷은 앞 장면을 같은 배율로 이어 보여 준다 — 시작은 장면이 바뀌는 때가 아니다(끝에서 바뀜)
            cuts.add(round(b, 3))
            cuts = {t for t in cuts if not (a - 0.01 <= t < b - 0.01)}
            continue
        cuts |= {round(a, 3), round(b, 3)}
        cuts = {t for t in cuts if not (a + 0.01 < t < b - 0.01)}  # 카드가 덮은 동안의 말 장면 컷은 안 보인다
    t = sorted(cuts)
    shots = []
    for a, b in zip(t, t[1:]):
        if b - a < 0.02:
            continue
        hit = next(((cid, comp) for x, y, cid, comp in spans if x - 0.01 <= a and b <= y + 0.01), ("말하는 장면", "talk"))
        shots.append((a, b, hit[0], hit[1]))
    d = [b - a for a, b, _, _ in shots]
 # 모션그래픽·화면 기록 장면(Screen 이 아닌 카드)은 장면 안 박자로 바뀌므로 "같은 그림"으로 세지 않는다(freezedetect 가 맡는다)
    long = [(a, b, n) for a, b, n, comp in shots[:-1] if b - a > mx and comp in ("talk", "Screen")]
    print(f"장면 {len(shots)}개, 가운데 값 {statistics.median(d):.2f}초, {mx}초 넘는 장면 {len(long)}곳")
    for a, b, n in long:
        print(f"  {a:6.2f}~{b:6.2f}  {b - a:.2f}초  {n}")


if __name__ == "__main__":
    main(sys.argv[1])
