#!/usr/bin/env python3
"""컷이 바뀐 뒤 3단계 효과 시간을 새 컷에 맞춰 옮긴다 (IMG_0519에서 컷을 여러 번 고치며 손으로 맞추다 장면 끝이 어긋났다).

사용법: remap.py <결과폴더> <옛 timemap.json> (cutplan을 다시 돌리기 전에 timemap.json을 옛_timemap.json 등으로 복사해 둔다)
옮기는 것: broll-plan.json(start·end, props.beats·items[].at·reportShot.views[].at — 장면 시작 기준 초라 절대 시각으로 바꿨다가 다시 상대로),
 overlays.json, sfx_후보.json, transition.json, title_dur.txt, zoom.json(조각 번호)
규칙: 옛 편집 시각 → (문장, 원본 시각) → 새 편집 시각. 원본 시각이 새 컷에서 잘려 나갔으면 그 문장의 다음 조각 시작으로.
 문장 경계(다음 문장 시작)에 있던 끝 시각은 새 컷의 그 문장 시작으로 — 장면 끝이 다음 문장으로 밀리지 않게.
끝나면 sfx_plan·captions·build_spec·카드 렌더를 다시 돌린다(시간이 바뀐 장면은 pip_prepare도).
"""
import json
import os
import sys


def main(res, old_path):
    old = json.load(open(old_path))
    new = json.load(open(os.path.join(res, "timemap.json")))
    first_old, first_new = {}, {}
    for s in old:
        first_old.setdefault(s["take"], s["start"])
    for s in new:
        first_new.setdefault(s["take"], s["start"])

    total = new[-1]["start"] + new[-1]["duration"]
    old_order = list(dict.fromkeys(s["take"] for s in old))

    def kept_from(take):  # 뺀 문장(맞장구·인트로 등)에 있던 시각 → 남은 다음 문장 시작, 없으면 끝
        for k in old_order[old_order.index(take):]:
            if k in first_new:
                return round(first_new[k], 4)
        return round(total, 4)

    def R(t):
        for k, v in first_old.items():  # 문장 시작에 있던 시각
            if abs(t - v) < 0.02 and k in first_new:
                return round(first_new[k], 4)
        for s in old:
            if s["start"] - 1e-6 <= t < s["start"] + s["duration"] - 1e-6:
                take, src = s["take"], s["src_in"] + (t - s["start"]) * s["speed"]
                break
        else:
            return round(total, 4)
        if take not in first_new:
            return kept_from(take)
        for s in new:
            if s["take"] == take and s["src_in"] - 1e-6 <= src <= s["src_out"] + 1e-6:
                return round(s["start"] + (src - s["src_in"]) / s["speed"], 4)
        for s in new:
            if s["take"] == take and src < s["src_in"]:
                return round(s["start"], 4)
        mine = [s for s in new if s["take"] == take]
        if mine and src > mine[-1]["src_out"]:  # 문장 끝을 줄여(군말 빼기) 잘려 나간 끝 → 그 문장의 새 끝
            return round(mine[-1]["start"] + mine[-1]["duration"], 4)
        last = new[-1]
        return round(first_new.get(take, last["start"] + last["duration"]), 4)

    p = json.load(open(os.path.join(res, "broll-plan.json")))
    for c in p["cards"]:
        s0, s1 = c["start"], R(c["start"])
        rel = lambda x: round(R(s0 + x) - s1, 3) if isinstance(x, (int, float)) and x >= 0 else x  # noqa: E731
        pr = c.get("props", {})
 # 장면 안 시간(장면 시작 기준 초)은 이름 규칙으로 한꺼번에 옮긴다 — at·…At·…End·beats 안 숫자.
 # 원본 쪽 시간(a·from·clips·rate·in)은 옮기지 않는다. RecScene shots 는 누적 경계를 옮긴 뒤 d 를 다시 잰다
 # (충돌 점검: showAt·chipAt·sendAt·typeEnd·flipAt·talkAt·marks[].at 를 못 옮겨 운영자 장면이 옛 시간에 남았다)
        if isinstance(pr.get("shots"), list) and pr["shots"] and all(isinstance(x, dict) and "d" in x for x in pr["shots"]):
            b0 = float(pr.get("showAt", 0) or 0)
            bounds = [b0]
            for x in pr["shots"]:
                bounds.append(bounds[-1] + float(x["d"]))
            nb = [rel(t) for t in bounds]
            for x, u, v in zip(pr["shots"], nb, nb[1:]):
                x["d"] = round(max(0.1, v - u), 3)
        def walk(o, timeish=False):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("a", "from", "clips", "rate", "in", "shots", "srcW", "srcH", "cropTop", "d", "speed", "scale", "pos"):
                        continue
                    t = timeish or k == "beats" or k == "at" or k.endswith("At") or k.endswith("End")
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        if t:
                            o[k] = rel(v)
                    else:
                        walk(v, t)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        if timeish:
                            o[i] = rel(v)
                    else:
                        walk(v, timeish)
        walk(pr)
        c["start"], c["end"] = round(round(s1 * 30) / 30, 4), round(round(R(c["end"]) * 30) / 30, 4)  # 프레임(1/30초) 단위로
    gone = [c["id"] for c in p["cards"] if c["end"] - c["start"] < 0.1]  # 뺀 문장에만 있던 장면
    p["cards"] = [c for c in p["cards"] if c["end"] - c["start"] >= 0.1]
    if gone:
        print("뺀 문장과 같이 빠진 장면:", ", ".join(gone))
    json.dump(p, open(os.path.join(res, "broll-plan.json"), "w"), ensure_ascii=False, indent=1)
    for f, keys in (("overlays.json", ("start", "end")), ("sfx_후보.json", ("t",))):
        fp = os.path.join(res, f)
        if os.path.exists(fp):
            o = json.load(open(fp))
            for x in o:
                for k in keys:
                    x[k] = R(x[k])
            if "end" in keys:
                gone = [x.get("text", "") for x in o if x["end"] - x["start"] < 0.1]
                o = [x for x in o if x["end"] - x["start"] >= 0.1]
                if gone:
                    print(f"뺀 문장과 같이 빠진 {f}:", ", ".join(gone))
            json.dump(o, open(fp, "w"), ensure_ascii=False, indent=1)
    fp = os.path.join(res, "transition.json")
    if os.path.exists(fp):
        tr = json.load(open(fp)); tr["at"] = R(tr["at"]); json.dump(tr, open(fp, "w"))
    fp = os.path.join(res, "title_dur.txt")
    if os.path.exists(fp):
        v = float(open(fp).read()); open(fp, "w").write(str(R(v)))
    fp = os.path.join(res, "zoom.json")
    if os.path.exists(fp):
        z = json.load(open(fp))
        def renum(d):  # 조각 번호로 적힌 값(scales·ramps·focus)을 새 컷의 조각 번호로
            out = {}
            for k, v in d.items():
                if old[int(k)]["take"] not in first_new:
                    continue  # 뺀 문장의 조각
                t0 = R(old[int(k)]["start"] + 0.05)
                out[str(max(i for i, s in enumerate(new) if s["start"] <= t0 + 1e-6))] = v
            return out
        for key in ("scales", "ramps", "focus"):
            if key in z:
                z[key] = renum(z[key])
        if isinstance(z.get("punch_at"), list):  # 편집본 시각으로 적힌 순간 확대
            z["punch_at"] = [[R(t), sc] for t, sc in z["punch_at"]]
        json.dump(z, open(fp, "w"), indent=1)
    print(json.dumps({"cards": [(c["id"], c["start"], c["end"]) for c in p["cards"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
