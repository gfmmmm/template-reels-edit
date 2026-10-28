#!/usr/bin/env python3
"""3단계 ③-C 효과음 계획 — 후보를 우선순위대로 받아 메뉴얼 9번 빈도 제한을 지키며 고른다.

사용법: sfx_plan.py <결과폴더> <후보.json>
후보: [{"t": 단어·화면 시각, "sfx": "21_쿵_무거운충격", "kind": "쿵", "prio": 1, "why": "...", "dur": 1.0, "vol_db": 0}]
 prio: 1 훅 > 2 자료화면 전환 > 3 강조 단어 > 4 기타. "ui": true = 모션그래픽 안 동작음(6dB 작게, 빈도 상한 제외, 0.5초 간격은 지킴)
 "on": "메모 글자"·"overlays id"·"카드 id" — 그 글자·장면에 붙은 소리("on_at": "end" 면 끝나는 때, "off": 초 만큼 더함). 있으면 t 를 overlays.json·broll-plan.json 의 그 시작 시각으로 다시 잡고,
 그 글자·장면이 없어졌으면 소리도 뺀다(메모·끝 문구를 옮겼는데 소리는 옛 시각에 남아 0.9초 앞서 났다. 대사로 바꾼 메모의 소리는 이유 없는 "뿅"으로 남았다).
 t는 소리가 들려야 할 시각. 휙과 "on" 으로 글자·장면에 묶인 짧은 소리(0.2초 안에 가장 커짐)는 가장 커지는 순간을 t에 맞추고(그만큼 앞당김),
 묶이지 않은 쿵·팝·띵은 시작을 t에 맞춘다(블라인드 시험: 메모에 묶은 바운스·팝업이 글자보다 0.1~0.15초 늦게 들렸다).
 끝에 효과음 없이 6초 넘게 비는 구간을 알린다 — 꿀팁·단계가 여럿이면 각 공개·결과 순간에 공개음이 있는지 본다(공용 규칙 70).
규칙(공용, — 사용자가 직접 넣은 IMG_0517 효과음 25개/25초 기준. 예전 0.5초·10초 4개·0.43개는 소리가 지루했다):
 효과음끼리 최소 0.2초, 10초 창에 최대 12개, 전체 1초당 1.1개 이하. 같은 소리 3번 연속은 휙(장면·카메라 이동)만 허용.
출력: sfx-plan.json / sfx-plan.md (넣은 것 + 뺀 것과 이유)
"""
import json
import os
import re
import sys

# 효과음 최고점 목표(dBFS). 들려야 하므로 너무 낮추지 않는다. 목소리와 겹쳐 최고점이 넘는 건 4단계에서
# 내보낸 파일의 소리만 리미터로 다듬어 해결한다(4_제출.md). 목소리는 전처리에서 최고 -2 dBTP.
TARGET = {"휙": -9, "띵": -12, "팝": -14, "쿵": -12, "타닥": -18}
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def catalog():
    rows = json.load(open(f"{SKILL}/sfx/palette_heard.json"))
    return {f"{r['no']:02d}_{r['ko_name']}": r for r in rows}


def main(res, cand_path):
    cat = catalog()
    cands = json.load(open(cand_path))
    anchors, dup = {}, set()
    if os.path.exists(f"{res}/overlays.json"):
        ovs = json.load(open(f"{res}/overlays.json"))
        texts = [o.get("text", "") for o in ovs]
        dup = {t for t in texts if texts.count(t) > 1}
        anchors.update({o.get("text", ""): (o["start"], o["end"]) for o in ovs if o.get("text", "") not in dup})
        anchors.update({o["id"]: (o["start"], o["end"]) for o in ovs if o.get("id")})  # 같은 글자가 둘이면 id 로 묶는다
    if os.path.exists(f"{res}/broll-plan.json"):
        anchors.update({c["id"]: (c["start"], c["end"]) for c in json.load(open(f"{res}/broll-plan.json")).get("cards", [])})
    for c in cands:
        if c.get("on") in dup:
            print(f'⚠ "{c["on"]}" 글자가 둘 이상이다 — overlays 줄에 "id" 를 주고 on 을 그 id 로(지금은 t 그대로)')
            c.pop("on")
    orphan = [c for c in cands if c.get("on") and c["on"] not in anchors]
    cands = [c for c in cands if c not in orphan]
    for c in cands:
        if c.get("on"):  # "on_at": "end" 면 끝나는 때(장면이 돌아오는 휙), 기본은 시작. "off" 초만큼 더한다
            a, b = anchors[c["on"]]
            c["t"] = round((b if c.get("on_at") == "end" else a) + float(c.get("off", 0)), 3)
    if orphan:
        print("붙은 글자·장면이 없어 뺀 효과음:", ", ".join(f'{c["sfx"]}({c["on"]})' for c in orphan))
    if os.path.exists(f"{res}/timemap.json"):  # 영상 길이 = 편집본 길이(마지막 단어 끝이 아니라 — 끝맺음 장면까지)
        tm = json.load(open(f"{res}/timemap.json"))
        dur = tm[-1]["start"] + tm[-1]["duration"]
    else:
        dur = max(w["e"] for w in json.load(open(f"{res}/편집본_단어시간.json")))
    cap_total = int(dur * 1.1)
    for c in cands:
        r = cat[c["sfx"]]
 # 쿵·팝·띵처럼 때리는 소리는 첫 타격이 귀에 들리는 순간 → 단어 시작에 그대로 맞춘다.
 # 휙처럼 차오르는 소리만 가장 커지는 순간을 화면 전환에 맞추려고 그만큼 앞당긴다.
        la = r.get("loudest_at") or 0
 # 휙은 가장 커지는 순간까지 통째로, 글자·장면에 묶인 소리는 짧게 때리는 소리(0.2초 안에 가장 커짐)만 그만큼 —
 # 울림이 긴 둥·이어지는 타자 소리는 가장 큰 때가 늦어도 시작이 곧 들리는 때라 그대로 둔다
        lead = la if c.get("kind") == "휙" else (la if c.get("on") and la <= 0.2 else 0)
        c["place"] = round(max(0.0, c["t"] - lead), 3)
        c["template"] = f"{SKILL}/sfx/{r['template']}"
 # 크기: 효과음 파일마다 원래 세기가 달라 일괄 dB로는 목소리와 합쳐질 때 넘친다.
 # 파일의 최고 세기(peak_db)를 재 둔 값으로, 효과음 최고점이 종류별 목표(TARGET, dBFS)가 되게 맞춘다.
        target = TARGET.get(c.get("kind"), -12) + c.get("vol_db", 0) + (-6 if c.get("ui") else 0)
        c["volume"] = round(min(2.0, 10 ** ((target - (r.get("peak_db") or 0)) / 20)), 3)
        c.setdefault("dur", min(1.2, r["dur"]))
    keep, drop = [], []
    for c in sorted(cands, key=lambda x: (x["prio"], x["t"])):
        why = None
        if any(abs(c["t"] - k["t"]) < 0.2 for k in keep):
            why = "다른 효과음과 0.2초 안"
 # "ui": 모션그래픽 장면 안 동작음(전송·스캔·팝업·체크). 작게 넣고 10초 4개·전체 상한에서 뺀다(모션그래픽엔 튀지 않는 효과음)
        elif not c.get("ui") and (lambda ts: any(ts[i + 12] - ts[i] < 10 for i in range(len(ts) - 12)))(sorted([k["t"] for k in keep if not k.get("ui")] + [c["t"]])):
            why = "10초에 12개 넘음"
        elif not c.get("ui") and len([k for k in keep if not k.get("ui")]) >= cap_total:
            why = f"전체 상한 {cap_total}개"
        (drop if why else keep).append({**c, **({"drop_why": why} if why else {})})
    keep.sort(key=lambda x: x["t"])
 # 같은 소리 3번 연속은 마지막에 전체 순서로 확인 (계획 도중 일부 목록으로 보면 잘못 걸린다)
    names = [k["sfx"] for k in keep]
    for i in range(len(names) - 2):
        if names[i] == names[i + 1] == names[i + 2] and keep[i + 1].get("kind") != "휙":
            print(f"경고: {keep[i + 1]['t']}초 근처 같은 소리 3번 연속 — 가운데 것을 다른 소리로 바꾼다")
    marks = [0.0] + [k["t"] for k in keep if not k.get("ui")] + [dur - 2.0]
    for a, b in zip(marks, marks[1:]):
        if b - a > 6:
            print(f"⚠ {a:.1f}~{b:.1f}초 {b - a:.1f}초 동안 효과음이 없다 — 그 사이 꿀팁·결과 공개 순간이 있으면 공개음을 넣는다(공용 70)")
    json.dump({"keep": keep, "drop": drop}, open(f"{res}/sfx-plan.json", "w"), ensure_ascii=False, indent=1)
    L = ["# 효과음 계획", "", f"영상 {dur:.1f}초, 넣은 효과음 {len(keep)}개 (1초당 {len(keep) / dur:.2f}개, 상한 {cap_total}개)", "",
         "| 시각(가장 큰 순간) | 놓는 위치 | 소리 | 크기 | 길이 | 이유 |", "|---|---|---|---|---|---|"]
    for k in keep:
        L.append(f"| {k['t']:.2f} | {k['place']:.2f} | {k['sfx']} | 최고 {TARGET.get(k.get('kind'), -12) + k.get('vol_db', 0)}dBFS (볼륨 {k['volume']}) | {k['dur']} | {k['why']} |")
    L += ["", "## 뺀 후보", ""] + [f"- {d['t']:.2f} {d['sfx']} — {d['drop_why']} ({d['why']})" for d in drop]
    open(f"{res}/sfx-plan.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
