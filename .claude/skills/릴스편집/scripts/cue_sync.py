#!/usr/bin/env python3
"""3단계 ③-A 모션그래픽을 대사에 맞춘다 — 장면 안 요소(박자·항목·표시)가 나오는 시각을 "그 요소를 말하는 단어"로 적으면
실제 단어 시각으로 바꿔 넣고, 숫자로만 적힌 박자는 말과 맞는지 검사한다(공용 규칙 69, "대사에 맞게 모션그래픽을 구성").
(지금까지는 AI가 박자를 "장면 시작 뒤 몇 초" 숫자로 직접 적었다 — 대개 맞았지만 컷을 고치면 틀어지고, 틀려도 아무도 몰랐다)

사용법: cue_sync.py <결과폴더> [--tol 0.15] (화면 계획 뒤 카드 렌더 전에, 컷을 고친 뒤에도 — rebuild.sh 가 부른다)
적는 법(broll-plan.json 카드 props 안 시간 자리에 숫자 대신 글자):
 "@단어" 그 카드 구간 안에서 처음 나오는 그 단어의 시작 (받아쓰기 단어가 이 글자로 시작하면 맞음 — "@정부" ↔ "정부에서")
 "@단어#2" 두 번째로 나오는 것
 "@단어>" 그 단어가 끝나는 때(…End 자리)
 "@단어+0.1" 시각에 초를 더하거나 빼기
 예) "beats": {"send": "@보내", "src": ["@정부", "@구글", "@인스타"]}, "items": [{"name": "심리상담", "at": "@심리상담"}]
 카드 시작·끝도 "startCue": "@이렇게", "endCue": "@다음>" 로 적으면 맞춘다.
처음 돌리면 글자를 숫자로 바꾸고 원래 글자는 카드 "cues" 에 남긴다 — 컷을 고친 뒤 다시 돌리면 그 글자로 다시 계산한다.
검사: 숫자로만 적힌 박자는 가장 가까운 단어 시작과 --tol 초 넘게 떨어져 있으면 "말과 안 맞음"으로 알린다(말 없는 효과 박자면 무시).
"""
import json
import re
import sys


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def norm(t):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", t or "")


def timeish(k):
    return k == "beats" or k == "at" or k.endswith("At") or k.endswith("End")


SKIP = ("a", "from", "clips", "rate", "in", "shots", "srcW", "srcH", "cropTop", "d", "speed", "scale", "pos")


def walk(o, path=(), ti=False):
    """(경로, 값, 시간 자리인가) 를 돌려준다."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP or k == "cues":
                continue
            t = ti or timeish(k)
            if isinstance(v, (dict, list)):
                yield from walk(v, path + (k,), t)
            else:
                yield path + (k,), v, t
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, (dict, list)):
                yield from walk(v, path + (i,), ti)
            else:
                yield path + (i,), v, ti


def put(o, path, v):
    for k in path[:-1]:
        o = o[k]
    o[path[-1]] = v


def resolve(cue, words, a, b):
    m = re.match(r"@([^#>+\-]+)(#\d+)?(>)?([+\-][0-9.]+)?$", cue.strip())
    if not m:
        return None
    w, nth, at_end, off = norm(m.group(1)), int((m.group(2) or "#1")[1:]), bool(m.group(3)), float(m.group(4) or 0)
    hits = [x for x in words if a - 0.3 <= x["s"] < b + 0.3 and norm(x["w"]).startswith(w)]
    if len(hits) < nth:
        return None
    x = hits[nth - 1]
    return (x["e"] if at_end else x["s"]) + off


def main(res):
    tol = arg("--tol", 0.15)
    words = json.load(open(f"{res}/편집본_단어시간.json"))
    plan = json.load(open(f"{res}/broll-plan.json"))
    onsets = sorted(x["s"] for x in words)
    fixed, bad, loose = 0, [], []
    for c in plan["cards"]:
        cues = c.setdefault("cues", {})
        pr = c.setdefault("props", {})
 # 새로 글자로 적힌 자리를 cues 에 옮겨 적는다
        for path, v, ti in list(walk(pr)):
            if isinstance(v, str) and v.startswith("@"):
                cues[".".join(map(str, path))] = v
        for key in ("startCue", "endCue"):
            if isinstance(c.get(key), str):
                cues["@" + key] = c[key]
 # 카드 시작·끝 먼저(장면 안 시간은 카드 시작 기준)
        for key, field in (("@startCue", "start"), ("@endCue", "end")):
            if key in cues:
                t = resolve(cues[key], words, c["start"] - 3, c["end"] + 3)
                if t is None:
                    bad.append((c["id"], field, cues[key]))
                else:
                    c[field] = round(round(t * 30) / 30, 4)
                    fixed += 1
        for p, cue in cues.items():
            if p.startswith("@"):
                continue
            t = resolve(cue, words, c["start"], c["end"])
            path = tuple(int(x) if x.isdigit() else x for x in p.split("."))
            if t is None:
                bad.append((c["id"], p, cue))
                continue
            try:
                put(pr, path, round(t - c["start"], 3))
                fixed += 1
            except (KeyError, IndexError, TypeError):
                bad.append((c["id"], p, cue + " (자리 없음)"))
        if not cues:
            c.pop("cues")
        bound = {tuple(int(x) if x.isdigit() else x for x in p.split(".")) for p in cues if not p.startswith("@")}
        for path, v, ti in walk(pr):
            if not ti or path in bound or not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                continue
            t = c["start"] + v
            gap = min((abs(t - s) for s in onsets), default=9)
            if gap > tol:
                loose.append((c["id"], ".".join(map(str, path)), round(v, 2), round(gap, 2)))
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
    print(f"대사에 묶인 시각 {fixed}개를 단어 시각으로 맞춤")
    for cid, p, cue in bad:
        print(f"  ✗ {cid} {p}: {cue} — 그 카드 구간에서 그 단어를 못 찾음(받아쓰기 글자 확인)")
    if loose:
        print(f"⚠ 단어와 {tol}초 넘게 떨어진 박자 {len(loose)}개 — 말에 맞출 요소면 \"@단어\"로 묶는다(말 없는 효과 박자면 그대로):")
        for cid, p, v, g in loose[:20]:
            print(f"  {cid} {p}={v} (가장 가까운 단어와 {g}초)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1])
