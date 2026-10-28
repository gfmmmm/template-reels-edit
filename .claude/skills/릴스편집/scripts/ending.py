#!/usr/bin/env python3
"""3단계 ③-A 3-1 끝맺음 — 마지막 말 뒤 반응 박자(평가 메모만) → 결과 장면 + 끝 문구만(공용 규칙 63).
(한 생활용품 계정 게시본 대조: 스킬은 평가 메모를 마지막 대사 자막과 겹쳐 띄우고 결과 장면에 감탄 자막과 끝 문구를
 같이 보여 줬다. 편집자는 대사가 끝난 뒤 메모만 1초 → 결과 장면에 끝 문구만 2초. 손으로 맞추다 효과음이 0.9초 어긋나기도 했다)

사용법: ending.py <결과폴더> [--beat 0.9] [--end-min 2.0] (cutplan·remap 다음, 카드·효과음 계획 전에. 컷을 고칠 때마다 다시)
표시(AI가 3단계에서 붙인다):
 overlays.json 평가 메모에 "role": "react", 끝 문구에 "role": "end"(없으면 tpl 이 "끝문구"로 시작하는 줄)
 broll-plan.json 결과 장면 카드에 "role": "result"
 셋 다 없으면 아무것도 하지 않는다 — 끝맺음은 계정 메뉴얼 7번이 결과 장면·끝 문구를 쓸 때만(공용 63, 튜토리얼형은 "행동 유도 후 바로 끝")
 자막_끊기.json 마지막 대사 뒤 감탄("와...")은 "-" 로 숨김 — 이 스크립트는 "숨기지 않은 마지막 자막"이 끝나는 때를 대사 끝으로 본다
규칙: 반응 박자 = 대사 끝 ~ +beat(평가 메모만), 결과 장면·끝 문구 = 그 뒤 ~ 영상 끝. 결과 장면이 end-min 보다 짧으면
 마지막 문장 edge_fix 끝을 원본 쪽으로 늘리라고 알리고(소리가 없으면 배경음악 자리) 멈춘다 → cutplan → ending.py 다시.
 효과음은 sfx_후보 "on" 으로 메모·끝 문구에 묶어 두면 따라온다.
"""
import json
import os
import sys


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def main(res):
    beat, end_min = arg("--beat", 0.9), arg("--end-min", 2.0)
    tm = json.load(open(f"{res}/timemap.json"))
    caps = json.load(open(f"{res}/captions.json")) if os.path.exists(f"{res}/captions.json") else []
    ovs = json.load(open(f"{res}/overlays.json"))
    plan = json.load(open(f"{res}/broll-plan.json"))
    total = tm[-1]["start"] + tm[-1]["duration"]
    shown = [c for c in caps if not c.get("hidden")]
    talk_end = max(c["end"] for c in shown) if shown else total
    if caps:  # 숨기지 않은 자막의 마지막 말이 끝나는 때(자막은 다음 자막까지 늘어나 있으니 그 문장 조각 끝으로)
        last_take = shown[-1].get("take")
        talk_end = max((s["start"] + s["duration"] for s in tm if s["take"] == last_take), default=talk_end)
    fr = lambda t: round(round(t * 30) / 30, 4)  # noqa: E731
    react0, fin = fr(talk_end), fr(talk_end + beat)
    react = [o for o in ovs if o.get("role") == "react"]
    if not react and not any(o.get("role") == "end" for o in ovs) and not any(c.get("role") == "result" for c in plan["cards"]):
        print("끝맺음 표시(role react·end·result)가 없다 — 이 계정은 끝맺음을 쓰지 않는다(메뉴얼 7번). 건너뜀")
        return
    short = end_min - (total - fin)
    if short > 0.02:
        last = tm[-1]
        need = round(last["src_out"] + short * last["speed"], 3)
        print(f"결과 장면이 {total - fin:.2f}초 — {end_min}초가 되려면 마지막 문장({last['take']}) edge_fix 끝을 {need} 로 늘린다"
              f"(원본 소리가 없으면 배경음악 자리) → cutplan.py → ending.py 다시")
        sys.exit(2)
    end = [o for o in ovs if o.get("role") == "end"] or [o for o in ovs if str(o.get("tpl", "")).startswith("끝문구")]
    for o in react:
        o["start"], o["end"] = react0, fin
    for o in end:
        o["start"], o["end"] = fin, fr(total)
    cards = [c for c in plan["cards"] if c.get("role") == "result"]
    for c in cards:
        c["start"], c["end"] = fin, fr(total)
    json.dump(ovs, open(f"{res}/overlays.json", "w"), ensure_ascii=False, indent=1)
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
    over = [c["text"] for c in shown if c["end"] > fin + 0.05]
    print(f"반응 박자 {react0}~{fin}(메모 {len(react)}개), 결과 장면 {fin}~{fr(total)} ({total - fin:.2f}초, 끝 문구 {len(end)}개)")
    if over:
        print("⚠ 결과 장면 위에 남는 자막 — 자막_끊기.json 에서 \"-\" 로 숨긴다:", ", ".join(over))


if __name__ == "__main__":
    main(sys.argv[1])
