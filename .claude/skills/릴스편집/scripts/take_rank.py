#!/usr/bin/env python3
"""2단계 ② 테이크 고르기 — 문장마다 후보 테이크에 점수를 매겨 고른다. 마지막 테이크는 가산점일 뿐 정답이 아니다.

사용법: take_rank.py <결과폴더> <편집용 영상>
입력: <결과폴더>/take_candidates.json {"문장번호": {"text": "교정 문장", "takes": [[덩어리 번호([첫 단어, 끝 단어])], ...]}}
 — 그 문장을 끝까지 말한 덩어리를 전부 넣는다(여러 문장을 이어 말한 덩어리는 단어 범위로 쪼개서).
 <결과폴더>/stt_chunks/chunks.json
출력: <결과폴더>/테이크후보.md (문장마다 후보 점수표), take_rank.json (문장마다 1위), 화면에 1위·2위
점수(100점 근처):
 대본 일치 — 교정 문장과 받아쓰기 글자 일치율 × 60
 매끄러움 — 원본 소리에서 말 사이 0.25초 넘게 멈춘 시간 합 × -25, 글자에 비해 긴 단어(반복·멈칫 신호) 하나당 -8
 말 속도 — 쉼 뺀 1초당 글자 6~10자 안이면 +10, 벗어나면 줄어든다
 뒤쪽 가산점 — 후보 순서대로 0~6점(마지막 테이크 +6). 점수가 비슷할 때만 결정을 가른다
2위와 5점 안쪽이면 "판단 갈림"으로 표시 → 진행상황.md에 적고 최종 보고에서 알린다.
IMG_0519: 마지막 테이크만 고르다 버벅인 테이크를 썼다(더 매끄러운 앞 테이크가 있었음) → 이 도구를 만듦.
"""
import difflib
import json
import os
import re
import subprocess
import sys

import numpy as np


def norm(s):
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s)


def pauses(video, a, b, th=-40.0, min_len=0.25):
    """원본 소리에서 [a, b] 안의 조용한 구간(th dB 아래가 min_len초 넘게) 목록"""
    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", video,
                          "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = int(sr * 0.02)
    if len(x) < hop:
        return []
    n = len(x) // hop
    rms = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    out, start = [], None
    for i, v in enumerate(list(rms) + [0.0]):
        if v < th and start is None:
            start = i
        elif v >= th and start is not None:
            if (i - start) * 0.02 >= min_len:
                out.append((a + start * 0.02, a + i * 0.02))
            start = None
    return out


def score(video, chunk, rng, text, order_bonus):
    w = chunk["words"][rng[0]:rng[1] + 1] if rng else chunk["words"]
    a, b = w[0]["s"], w[-1]["e"]
    heard = "".join(x["w"] for x in w)
    match = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
    ps = pauses(video, a + 0.05, b - 0.05)
    pause_sum = sum(e - s for s, e in ps)
    longw = [x["w"] for x in w if (x["e"] - x["s"]) > 0.8 and (x["e"] - x["s"]) > 0.35 * len(x["w"]) + 0.3]
    speech = max(0.3, (b - a) - pause_sum)
    cps = len(norm(heard)) / speech
    rate = 10 if 6 <= cps <= 10 else max(0, 10 - 3 * min(abs(cps - 6), abs(cps - 10)))
    total = 60 * match - 25 * pause_sum - 8 * len(longw) + rate + order_bonus
    return {"score": round(total, 1), "match": round(match, 2), "pause": round(pause_sum, 2), "long": longw,
            "cps": round(cps, 1), "bonus": round(order_bonus, 1), "src": [round(a, 2), round(b, 2)], "heard": heard}


def main(res, video):
    cand = json.load(open(os.path.join(res, "take_candidates.json")))
    chunks = {c["i"]: c for c in json.load(open(os.path.join(res, "stt_chunks", "chunks.json")))}
    best, md = {}, ["# 테이크 후보 점수", "", "점수 = 대본 일치×60 − 멈춘 시간×25 − 긴 단어×8 + 말 속도(0~10) + 뒤쪽 가산점(0~6)", ""]
    for num, c in sorted(cand.items(), key=lambda kv: int(kv[0])):
        takes = c["takes"]
        rows = []
        for k, t in enumerate(takes):
            ci, rng = t[0], (t[1] if len(t) > 1 else None)
            bonus = 6 * k / (len(takes) - 1) if len(takes) > 1 else 0
            r = score(video, chunks[ci], rng, c["text"], bonus)
            r["take"] = [ci] + ([rng] if rng else [])
            rows.append(r)
        rows.sort(key=lambda r: -r["score"])
        close = len(rows) > 1 and rows[0]["score"] - rows[1]["score"] < 5
        best[num] = {"take": rows[0]["take"], "score": rows[0]["score"], "close": close}
        md += [f"## {num}. {c['text']}" + ("  ⚠ 판단 갈림" if close else ""), "",
               "| 순위 | 덩어리 | 점수 | 일치 | 멈춤(초) | 긴 단어 | 1초당 글자 | 뒤쪽 | 받아쓰기 |", "|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(rows):
            md.append(f"| {i + 1} | {r['take']} | {r['score']} | {r['match']} | {r['pause']} | {' '.join(r['long']) or '-'} | {r['cps']} | {r['bonus']} | {r['heard']} |")
        md.append("")
        second = f" / 2위 {rows[1]['take']} {rows[1]['score']}" if len(rows) > 1 else ""
        print(f"{num}: 1위 {rows[0]['take']} {rows[0]['score']}{second}{'  ⚠ 판단 갈림' if close else ''}")
    open(os.path.join(res, "테이크후보.md"), "w").write("\n".join(md))
    json.dump(best, open(os.path.join(res, "take_rank.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
