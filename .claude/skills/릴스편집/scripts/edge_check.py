#!/usr/bin/env python3
"""2단계 ③ 점검 — 문장 끝·첫소리가 잘렸는지 원본 소리로 본다(받아쓰기는 잘린 소리를 채워 들어서 못 믿는다).
(블라인드 시험: 앞 편집본은 끝 단어를 음절 사이 0.08초 골에서 잘라 마지막 음절이 통째로 빠졌고, 펀치 문장
 끝이 -22dB 인 채로 툭 끊겼다. 블라인드 편집은 ㅅ·ㅊ 첫소리와 끝모음 5곳이 잘렸다. 다시 받아쓴 글자로는 끝 음절이
 비슷한 말로만 바뀌어 오인식처럼 보였고, 검수 에이전트가 화면·숫자로 잡기 전까지 아무도 몰랐다)

사용법: edge_check.py <결과폴더> <편집용 영상> [--fix] (cutplan·edge_snap·gap_trim 다음, 그리고 rebuild.sh 가 매번)
본다: 남긴 문장마다(timemap 의 문장 첫 조각 시작·마지막 조각 끝, 원본 시각)
 끝 — 자른 자리 뒤 0.12초 안에 그 문장 말소리 크기(위 10% - 15dB)의 소리가 40ms 넘게 이어지면 "말끝 잘림 의심".
 원본에서 바로 이어지는 다음 남긴 문장이면 아니다. 이어지는 소리가 0.45초 넘게 계속되면 다른 말(뺀 단어)로 보고 넘긴다.
 시작 — 자른 자리 앞 0.1초 안에서 말소리가 끝나거나, 높은 소리 띠(2.5kHz 위, ㅅ·ㅊ 마찰음)가 시작점까지 이어지면 "첫소리 잘림 의심".
--fix: 의심 자리를 edge_fix.json 에 넓혀 적는다(끝 = 이어진 소리 끝 + 0.05초, 시작 = 이어진 소리 시작 - 0.02초) → cutplan.py 다시.
 nocut.json 문장은 보지 않는다. 고친 뒤에도 남으면 들어 보고 판단한다(같은 숨이 걸렸을 수 있다).
"""
import json
import os
import sys

HISS = {9, 10, 12, 13, 14, 15, 16, 17, 18}  # 첫소리가 ㅅ ㅆ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ — 높은 소리 띠로만 보이는 자음


def hiss_first(text):
    """문장 첫 글자가 마찰·거센소리로 시작하나(모음·ㄴ·ㅁ 으로 시작하면 높은 소리 띠는 다른 소리다)."""
    ch = next((c for c in text if "가" <= c <= "힣"), "")
    return bool(ch) and (ord(ch) - 0xAC00) // 588 in HISS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_snap import env  # noqa: E402


def main(res, video):
    fixing = "--fix" in sys.argv
    tm = json.load(open(f"{res}/timemap.json"))
    order, span = [], {}
    for p in tm:
        n = p["take"]
        if n not in span:
            order.append(n)
        a, b = span.get(n, (1e9, -1))
        span[n] = (min(a, p["src_in"]), max(b, p["src_out"]))
    nocut = set()
    if os.path.exists(f"{res}/nocut.json"):
        nc = json.load(open(f"{res}/nocut.json"))
        nocut = {int(k) if str(k).isdigit() else k for k in (nc if isinstance(nc, list) else nc.keys())}
    fix = json.load(open(f"{res}/edge_fix.json")) if os.path.exists(f"{res}/edge_fix.json") else {}
    takes = {tk[0]: tk for tk in json.load(open(f"{res}/takes.json"))}
    try:
        chunks = json.load(open(f"{res}/stt_chunks/chunks.json"))
    except FileNotFoundError:
        chunks = []

    def words_of(n):
        """(첫 단어, 끝 단어, 앞 단어, 뒤 단어) — 받아쓰기 원본 시각. 앞·뒤는 같은 덩어리의 이웃 단어(없으면 None)"""
        tk = takes.get(n)
        if not tk or len(tk) < 4 or not (0 <= tk[2] < len(chunks)):
            return None
        W = chunks[tk[2]].get("words", [])
        w0, w1 = tk[3]
        if not (0 <= w0 <= w1 < len(W)):
            return None
        return W[w0], W[w1], (W[w0 - 1] if w0 > 0 else None), (W[w1 + 1] if w1 + 1 < len(W) else None)
    starts = sorted(v[0] for v in span.values())
    found = []
    for n in order:
        if n in nocut or isinstance(n, str):
            continue
        a, b = span[n]
        t0, hop, db = env(video, a, b)
        sp = [x for x in db if x > -50]
        if len(sp) < 10:
            continue
        lvl = sorted(sp)[int(len(sp) * 0.9)] - 15
 # 끝
        nxt_kept = any(b - 0.05 <= s <= b + 0.3 for s in starts)
        ws = words_of(n)
 # 뒤에 바로 붙은 소리가 뺀 단어(덧말·맞장구)면 일부러 자른 자리다: 끝 단어가 자른 자리 안에서 끝나고 다음 단어가 0.15초 안에 시작
        drop_next = bool(ws and ws[3] and ws[1]["e"] <= b + 0.06 and ws[3]["s"] <= b + 0.15)
        if not nxt_kept and not drop_next:
            e0, hop, de = env(video, b, b + 0.7)
            run = [j for j in range(len(de) - 3) if min(de[j:j + 4]) > lvl]
            if run and run[0] * hop <= 0.12:
                k = run[0]
                while k < len(de) - 1 and de[k + 1] > lvl - 6:
                    k += 1
                tail = (k + 1) * hop
                if tail <= 0.45:
                    found.append((n, "end", b, round(b + tail + 0.05, 3), f"자른 자리 뒤 {run[0] * hop:.2f}초부터 {tail:.2f}초까지 말소리"))
 # 시작
        prv_kept = any(a - 0.3 <= v[1] <= a + 0.05 for k2, v in span.items() if k2 != n)
        drop_prev = bool(ws and ws[2] and ws[0]["s"] >= a - 0.06 and ws[2]["e"] >= a - 0.15)
        if not prv_kept and not drop_prev:
            s0, hop, ds = env(video, a - 0.4, a)
            _, _, hs = env(video, a - 0.4, a + 0.1, af="highpass=f=2500")
            m = len(ds)
            voiced = [j for j in range(m - 3) if min(ds[j:j + 4]) > lvl]
            new = None
            if voiced and (m - 1 - voiced[-1]) * hop <= 0.1:
                j = voiced[-1]
                while j > 0 and ds[j - 1] > lvl - 6 and (m - j) * hop < 0.4:
                    j -= 1
                if (m - j) * hop <= 0.25:  # 더 길면 다른 말(앞 테이크·뺀 단어)이다
                    new = a - (m - j) * hop
                    why = f"자른 자리 앞 {(m - j) * hop:.2f}초부터 말소리"
            if hs and hiss_first((takes.get(n) or [0, ""])[1]):
                floor = sorted(hs)[max(0, int(len(hs) * 0.1))]
                j = min(m, len(hs)) - 1
                if hs[j] > floor + 15:
                    while j > 0 and hs[j - 1] > floor + 15 and (m - j) * hop < 0.15:
                        j -= 1
                    if (m - j) * hop >= 0.03:
                        c = a - (m - j) * hop
                        if new is None or c < new:
                            new, why = c, f"자른 자리 앞 {(m - j) * hop:.2f}초부터 높은 소리 띠(ㅅ·ㅊ 첫소리)"
            if new is not None:
                found.append((n, "start", a, round(new - 0.02, 3), why))
 # 앞 문장 꼬리 조각: 문장 첫 조각이 0.3초 안 되고, 원본에서 앞 문장 끝에 붙어 있고, 다음 조각과는 떨어져 있으면
 # 앞 문장 끝소리가 이 문장 첫머리로 딸려 온 것이다(블라인드 시험: "했는데" 꼬리 0.23초가 다음 문장 첫 조각으로)
    for n in order:
        ps = [p for p in tm if p["take"] == n]
        if len(ps) < 2 or n in nocut:
            continue
        p0, p1 = ps[0], ps[1]
        if (p0["src_out"] - p0["src_in"] < 0.3 and abs(p1["src_in"] - p0["src_out"]) > 0.05
                and any(abs(v[1] - p0["src_in"]) <= 0.05 for k2, v in span.items() if k2 != n)):
            found.append((n, "start", p0["src_in"], round(p1["src_in"] - 0.03, 3), f"첫 조각 {p0['src_out'] - p0['src_in']:.2f}초가 앞 문장 꼬리"))
    for n, side, old, new, why in found:
        print(f"⚠ 문장 {n} {'말끝' if side == 'end' else '첫소리'} 잘림 의심 — 원본 {old:.3f} → {new:.3f} ({why})")
        if fixing:
            f = fix.get(str(n), {})
            f[side] = new
            fix[str(n)] = f
    if fixing and found:
        json.dump(fix, open(f"{res}/edge_fix.json", "w"), indent=0)
        print("edge_fix.json 에 넓혀 적음 → cutplan.py 를 다시 돌린 뒤 edge_check 를 한 번 더")
    print(f"말끝·첫소리 잘림 의심 {len(found)}곳")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
