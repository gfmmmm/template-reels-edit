#!/usr/bin/env python3
"""3단계 ③-A 자막 덩어리 나누기 — 교정 대본 글자에 편집본 단어 시간을 입혀 1줄 자막으로 나눈다.

사용법: captions.py <결과폴더> [--max-chars 10] [--max-words 3]
입력: takes.json(교정 문장), 편집본_단어시간.json, 자막_끊기.json(AI가 쓴 끊기·표시)
출력: captions.json [{i, start, end, text, color, ranges, big, hidden}]
자막_끊기.json 표시(메뉴얼 5번): {"문장번호": "덩어리 / *노랑 덩어리 / !빨강 덩어리 / ^크게 / -숨김"}
 - 덩어리 글자는 화면에 나갈 글 그대로(맞춤법·느낌표·말줄임 다듬은 것). 시간은 글자 비율로 맞춘다.
 - {중괄호} 안만 노랑(부분 칠하기): "{크리에이터}라면" → ranges [[0,5]]
 - -숨김: 라벨이 대신 나오는 나열 구간처럼 자막을 끄는 덩어리(시간은 차지)
규칙: 1줄, 공백 포함 max-chars자 이하, 뜻 단위 먼저, 표시 시간은 다음 자막 시작까지(빈틈 없음), 최소 0.2초.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

BREAK_AFTER = ("은", "는", "을", "를", "에서", "에게", "한테", "하고", "해서", "하면", "면", "까지", "부터",
               "중에서", "는데", "인데", "니까", "서", ",", ".", "?", "!", "요", "다")


def arg(n, d):
    return int(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def char_times(words):
    """받아쓰기 단어 → 글자마다 시간 (단어 안에서 고르게)."""
    out = []
    for w in words:
        cs = re.sub(r"\s", "", w["w"])
        n = max(1, len(cs))
        for k in range(n):
            out.append(w["s"] + (w["e"] - w["s"]) * k / n)
    return out


MANUAL = {}


def snap_to_cuts(res, caps, near=0.08):
    """자막이 바뀌는 프레임을 장면이 바뀌는 프레임에 맞춘다(공용 규칙 — 2026-10-28 블라인드 시험: 새 장면 첫 프레임에 자막이 비거나
    앞 자막이 새 장면에 1~2프레임 남았다). 장면 경계 = 말 영상 원본이 이어지지 않는 곳 + 자료화면 카드 시작·끝.
    near 초 안에 경계가 있으면 그 프레임으로, 없으면 1/30초 격자로. 앞 자막과 0.15초 안으로 붙게 되면 옮기지 않는다."""
    cuts = set()
    if os.path.exists(f"{res}/timemap.json"):
        tm = json.load(open(f"{res}/timemap.json"))
        for p, s in zip(tm, tm[1:]):
            if abs(s["src_in"] - p["src_out"]) > 0.05 or s.get("take") != p.get("take"):
                cuts.add(round(s["start"], 4))
    if os.path.exists(f"{res}/broll-plan.json"):
        for c in json.load(open(f"{res}/broll-plan.json")).get("cards", []):
            cuts |= {round(c["start"], 4), round(c["end"], 4)}
    cuts = sorted(cuts)
    prev = -1.0
    for c in caps:
        b = min(cuts, key=lambda x: abs(x - c["start"]), default=None)
        t = b if b is not None and abs(b - c["start"]) <= near else round(c["start"] * 30) / 30
        if t > prev + 0.15:
            c["start"] = round(t, 4)
        prev = c["start"]


def warn_big_memo(res, caps):
    """큰 글자(리액션_흔들림 같은 화면 가운데 큰 메모)가 떠 있는 동안 대사 자막이 같이 뜨면 알린다 — 큰 글자 두 줄이 한꺼번에 뜨면
    어디를 읽을지 갈린다. 메모와 같은 결의 대사면 자막 덩어리에 "-"(숨김)를 붙인다(공용 규칙 71)."""
    if not os.path.exists(f"{res}/overlays.json"):
        return
    big = [o for o in json.load(open(f"{res}/overlays.json"))
           if str(o.get("tpl", "")).startswith("리액션") or o.get("big")]
    for o in big:
        hit = [c for c in caps if not c.get("hidden") and c["start"] < o["end"] - 0.1 and c["end"] > o["start"] + 0.1]
        if hit:
            print(f"⚠ 큰 글자 \"{o.get('text', '')}\"({o['start']:.2f}~{o['end']:.2f}) 아래 대사 자막이 같이 뜬다: "
                  + ", ".join(f"'{c['text']}'" for c in hit) + " — 숨길지 본다(공용 71)")


def main(res):
    global MANUAL
    if os.path.exists(f"{res}/자막_끊기.json"):  # {"문장번호": "덩어리 / *노랑 덩어리 / !빨강 덩어리"}
        MANUAL = json.load(open(f"{res}/자막_끊기.json"))
    mc, mw = arg("--max-chars", 10), arg("--max-words", 3)
    takes = json.load(open(f"{res}/takes.json"))
    words = json.load(open(f"{res}/편집본_단어시간.json"))
    caps = []
    units = [(tk[0], tk[1]) for tk in takes]
 # 나레이션 문장도 같은 규칙으로 자막을 만든다(단어 시간은 narration_apply 가 take=<id> 로 넣어 둔 것)
    units += [(it["id"], it["text"]) for it in pu.load_narration(res)]
    for n, text in units:
        ws = [w for w in words if w["take"] == n]
        ct = char_times(ws)
        toks = text.replace(",", ", ").split()
        total = sum(len(t) for t in toks)
 # 교정 문장 글자 위치 → 받아쓰기 글자 시간 (비율로 맞춤: 표기 차이가 있어도 시간이 밀리지 않게)
        def t_at(pos):
            if not ct:
                return 0
            return ct[min(len(ct) - 1, int(pos / max(1, total) * len(ct)))]
        groups, cur = [], []
        manual = MANUAL.get(str(n))
        if manual:  # AI가 직접 정한 끊기: "덩어리1 / 덩어리2 / ..." (색은 앞에 *노랑 !빨강)
            for part in [p.strip() for p in manual.split("/")]:
                groups.append(part.split())
            toks = []
        for tok in toks:
            cand = " ".join(cur + [tok])
            if cur and (len(cand) > mc or len(cur) >= mw):
                groups.append(cur)
                cur = [tok]
            else:
                cur.append(tok)
                if len(cur) >= 2 and tok.endswith(BREAK_AFTER) and len(" ".join(cur)) >= 6:
                    groups.append(cur)
                    cur = []
        if cur:
            groups.append(cur)
        pos = 0
        clean = lambda x: x.lstrip("*!^-").replace("{", "").replace("}", "")
        total = sum(len(clean(t)) for g in groups for t in g)
        for g in groups:
            raw = " ".join(g)
            body = raw.lstrip("*!^-").strip()
            mark = raw[:len(raw) - len(raw.lstrip("*!^-"))]  # 여러 개 가능: "^*2탄도" = 크게 + 노랑
            color = "yellow" if "*" in mark else "red" if "!" in mark else "white"
            if not manual:
                body = body.rstrip(",. ")
            ranges, txt, k = [], "", 0
            for part in body.replace("}", "{").split("{"):
                if k % 2 and part:
                    ranges.append([len(txt), len(txt) + len(part)])
                txt += part
                k += 1
            cap = {"take": n, "start": round(t_at(pos), 3), "text": txt, "color": color}
            if ranges:
                cap["ranges"] = ranges
            if "^" in mark:
                cap["big"] = True
            if "-" in mark:
                cap["hidden"] = True
            caps.append(cap)
            pos += len(txt.replace(" ", ""))
 # 번호 장 카드(어두운 화면 + 번호)가 떠 있는 동안은 자막을 숨긴다(사용자: 대사가 안 나와도 된다)
    if os.path.exists(f"{res}/broll-plan.json"):
        chap = [(c["start"], c["end"]) for c in json.load(open(f"{res}/broll-plan.json"))["cards"] if c["component"] == "ChapterCard"]
        for c in caps:
            if any(a - 0.02 <= c["start"] < b - 0.05 for a, b in chap):
                c["hidden"] = True
    end_all = max(w["e"] for w in words)
    caps.sort(key=lambda c: c["start"])  # 나레이션 자막이 시간 순서에 끼어들게
    snap_to_cuts(res, caps)
 # 같은 시각에 두 자막이 겹치면(나레이션 over 가 원래 말과 겹친 경우) 길이 0 자막이 생겨 CapCut compile 이 거부한다 → 0.1초 미만은 빼고 다시 잇는다
    for _ in range(2):
        for i, c in enumerate(caps):
            nxt = caps[i + 1]["start"] if i + 1 < len(caps) else end_all
            c["end"] = round(nxt if i + 1 < len(caps) else max(c["start"] + 0.2, nxt), 3)  # 다음 자막과 겹치지 않게
        short = [c for c in caps if c["end"] - c["start"] < 0.1]
        if not short:
            break
        print(f"경고: 다른 자막과 겹쳐 뺀 자막 {len(short)}개 — " + ", ".join(f"{c['start']:.2f} '{c['text']}'" for c in short[:4]))
        caps = [c for c in caps if c["end"] - c["start"] >= 0.1]
    for i, c in enumerate(caps):
        c["i"] = i
        c.setdefault("color", "white")
    warn_big_memo(res, caps)
    json.dump(caps, open(f"{res}/captions.json", "w"), ensure_ascii=False, indent=1)
    shown = [c for c in caps if not c.get("hidden")]
    lens = [len(c["text"]) for c in shown]
    emph = sum(1 for c in shown if c["color"] != "white" or c.get("ranges"))
    print(f"자막 {len(shown)}개(숨김 {len(caps) - len(shown)}), 글자 수(공백 포함) 최대 {max(lens)}, {mc}자 넘는 것 {sum(l > mc for l in lens)}, "
          f"강조 {emph}개({emph / len(shown):.0%}), 빨강 {sum(c['color'] == 'red' for c in shown)}")
    for c in caps:
        tag = (c["color"][0] if c["color"] != "white" else " ") + ("^" if c.get("big") else " ") + ("-" if c.get("hidden") else " ")
        print(f"{c['i']:3d} {c['start']:6.2f}-{c['end']:6.2f} {tag} {c['text']} {c.get('ranges', '')}")


if __name__ == "__main__":
    main(sys.argv[1])
