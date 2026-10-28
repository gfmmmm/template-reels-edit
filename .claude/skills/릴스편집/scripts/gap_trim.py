#!/usr/bin/env python3
"""2단계 ③ 1-1b 문장 앞뒤의 말 아닌 소리(숨·손 소리·방 소리)를 덜어낸다 — edge_snap 다음에 돌린다.
(한 생활용품 계정 게시본 대조: edge_snap 은 -38dB 소리를 따라가서 말끝 뒤 숨·손 소리까지 문장에 넣었다 —
 대사 부분이 편집자보다 7% 늘어졌다. 받아쓰기로 "단어가 남았나"를 확인하며 바짝 자르는 방법은 받아쓰기가 잘린 끝소리를
 채워 들어서 "좋고"·"진짜"가 잘렸다 → 소리 크기로만, 보수적으로)

사용법: gap_trim.py <결과폴더> <편집용 영상> [--keep 1,4] [--turn 9,13] [--drop 20] [--tail 0.04] [--lead 0.03]
 --turn: 두 사람이 주고받는 영상에서 질문 문장(끝)·대답 문장(시작) 번호 — 0.1초 숨을 남긴다(공용 68). 혼자 말하는 계정은 안 씀
 --drop: 혼자 말하는 계정에서 약한 말끝("~습니다")이 잘리면 계정 메뉴얼 13번 값으로 키운다
 영상 마지막 문장 끝과 nocut.json 문장은 건드리지 않는다(공용 18)
규칙: 문장 안 큰 말소리(10ms 단위, 위 10% 값)보다 --drop dB 이상 작은 소리는 "말 아님"(숨·방 소리 -39~-48dB가 여기 든다 —
 가운데 값 기준으로는 이걸 말로 쳐서 0.05초밖에 못 덜었다. 평가: 이음매 10곳에 1.5초가 남아 있었다).
 끝: 마지막으로 말소리 크기(끝은 6dB 더 너그럽게 — 늘어지는 끝모음 꼬리) 안에 드는 곳 + --tail.
 시작: 처음 드는 곳 - --lead. 다만 그 앞 0.2초 안에 높은 소리 띠(2.5kHz 위)가 바닥보다 15dB 넘게 30ms 이어지면
 거기서 시작한다 — ㅅ·ㅊ 마찰음은 전체 크기로는 숨만큼 작다(블라인드 시험: ㅅ·ㅊ 첫소리 2곳과
 끝모음 3곳이 잘렸다).
 덜어낸 뒤 반드시 2단계 ③ 점검 3(미리보기 다시 받아쓰기 → 교정 대본과 글자 대조)으로 빠진 말이 없는지 본다. 빠진 문장은 --keep 으로 되돌린다.
출력: edge_fix.json 갱신 → cutplan.py 를 다시 돌린다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_snap import arg, env  # noqa: E402
from edge_check import hiss_first  # noqa: E402


def main(res, video):
    drop, tail, lead = arg("--drop", 20.0), arg("--tail", 0.04), arg("--lead", 0.03)
    keep = {int(k) for k in arg("--keep", "").split(",") if k.strip()}
    takes = json.load(open(f"{res}/takes.json"))
    text_of = {tk[0]: tk[1] for tk in takes}
    tm = json.load(open(f"{res}/timemap.json"))
    fix = json.load(open(f"{res}/edge_fix.json")) if os.path.exists(f"{res}/edge_fix.json") else {}
    span = {}
    for p in tm:
        a, b = span.get(p["take"], (1e9, -1))
        span[p["take"]] = (min(a, p["src_in"]), max(b, p["src_out"]))
    order = [tk[0] for tk in takes if tk[0] in span]
    nocut = set()
    if os.path.exists(f"{res}/nocut.json"):
        nc = json.load(open(f"{res}/nocut.json"))
        nocut = {int(k) for k in (nc if isinstance(nc, list) else nc.keys())}
    turn = {int(k) for k in arg("--turn", "").split(",") if k.strip()}  # 두 사람 영상: 질문 문장 끝·대답 문장 시작에 0.1초 숨
    saved = 0.0
    for k, n in enumerate(order):
        if n in keep or n in nocut:
            continue
        a, b = span[n]
        t0, hop, db = env(video, a, b)
        sp = [x for x in db if x > -50]
        if len(sp) < 10:
            continue
        lvl = sorted(sp)[int(len(sp) * 0.9)] - drop
 # 30ms 이상 이어진 소리만 말로 친다 — 컷 첫머리 딸깍 소리 한 프레임 때문에 앞 숨 0.16초를 못 덜었다
        loud = [j for j in range(len(db) - 2) if min(db[j:j + 3]) > lvl]
        if not loud:
            continue
        loud = loud + [loud[-1] + 1, loud[-1] + 2]
        tail_lvl = lvl - 6  # 끝모음 꼬리는 더 작게 줄어든다
        tl = [j for j in range(len(db) - 2) if min(db[j:j + 3]) > tail_lvl]
        last = max(loud[-1], (tl[-1] + 2) if tl else 0)
        f = fix.get(str(n), {})
        if n != order[-1]:  # 끝 — 영상 마지막 말은 cutplan --last-tail 여유를 그대로(공용 18)
            e = t0 + (last + 1) * hop + (0.1 if n in turn else tail)
            if b - e > 0.04:
                f["end"] = round(e, 3)
                saved += b - e
        if True:  # 시작 — 마찰음 첫소리는 높은 소리 띠로 찾는다
            first = loud[0]
            _, _, hf = env(video, a, b, af="highpass=f=2500")
            if hf and hiss_first(text_of.get(n, "")):
                floor = sorted(hf)[max(0, int(len(hf) * 0.1))]
 # 말소리 바로 앞에 붙어 이어지는 높은 소리 띠만 첫소리로 친다(떨어져 있는 숨소리는 덜어낸다)
                j = min(first, len(hf) - 1)
                while j > 0 and first - j < 15 and hf[j - 1] > floor + 15:
                    j -= 1
                if first - j >= 3:
                    first = j
            s = t0 + first * hop - (0.1 if n in turn else lead)
            if s - a > 0.04:
                f["start"] = round(s, 3)
                saved += s - a
        if f:
            fix[str(n)] = f
    json.dump(fix, open(f"{res}/edge_fix.json", "w"), indent=0)
    print(f"문장 앞뒤 말 아닌 소리 {saved:.2f}초 덜어냄 → cutplan.py 를 다시 돌린다")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
