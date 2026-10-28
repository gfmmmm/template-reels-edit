#!/usr/bin/env python3
"""NG(다시 말하기) 감지 기준값 보정 — 정답지 원본 받아쓰기(SRT)에 detect-retakes를 돌려
사용자가 실제로 버린 앞 테이크를 가장 잘 잡는 값을 찾는다.

사용법: calibrate_retakes.py <profile.json> <원본.srt> <원본 파일명 일부> <출력.json>
정답(버려야 할 줄): 정답지가 쓰지 않은 줄 중, 뒤에 비슷한 말(문자 유사도 0.6 이상)을 한 줄이 정답지에 쓰인 것.
"""
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))
from calibrate_silence import kept_spans  # noqa: E402


def parse_srt(path):
    cues = []
    for block in open(path, encoding="utf-8").read().strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        a, b = re.findall(r"(\d+):(\d+):(\d+)[,.](\d+)", lines[1])[:2]
        ts = lambda h, m, s, ms: int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        cues.append({"start": ts(*a), "end": ts(*b), "text": " ".join(lines[2:])})
    return cues


def overlaps(c, spans):
    return any(min(c["end"], b) - max(c["start"], a) > 0.2 for a, b in spans)


def norm(t):
    return re.sub(r"[^\w]", "", t)


def truth(cues, kept):
    used = [overlaps(c, kept) for c in cues]
    cut = set()
    for i, c in enumerate(cues):
        if used[i]:
            continue
        for j in range(i + 1, len(cues)):
            if used[j] and SequenceMatcher(None, norm(c["text"]), norm(cues[j]["text"])).ratio() >= 0.6:
                cut.add(i)
                break
    return cut, used


def run(srt, mw, sim, win):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:
        subprocess.run(["capcut", "detect-retakes", "--srt", srt, "--min-words", str(mw),
                        "--similarity", str(sim), "--window", str(win), "--json"], stdout=fh)
    d = json.load(open(tmp))
    os.unlink(tmp)
    return [(x["start"], x["end"]) for x in d.get("cuts", [])]


def main(profile, srt, key, out):
    kept = kept_spans(json.load(open(profile)), key)
    cues = parse_srt(srt)
    cut_truth, used = truth(cues, kept)
    res = []
    for mw, sim, win in itertools.product([1, 2, 3, 4], [0.5, 0.6, 0.7, 0.8], [30, 60, 120]):
        pred = run(srt, mw, sim, win)
        hit = {i for i, c in enumerate(cues) if any(abs(c["start"] - a) < 0.05 for a, _ in pred)}
        tp = len(hit & cut_truth)
        wrong = len([i for i in hit if used[i]])  # 정답지가 쓴 줄을 자르라고 한 경우 (가장 나쁨)
        p = tp / len(hit) if hit else 0
        r = tp / len(cut_truth) if cut_truth else 0
        f1 = 2 * p * r / (p + r) if p + r else 0
        res.append({"min_words": mw, "similarity": sim, "window": win, "f1": round(f1, 3),
                    "precision": round(p, 3), "recall": round(r, 3), "cuts_used_line": wrong})
    res.sort(key=lambda x: (-x["recall"] if x["cuts_used_line"] <= 3 else 9, -x["f1"]))
    default = next(x for x in res if (x["min_words"], x["similarity"], x["window"]) == (4, 0.8, 60))
    json.dump({"best": res[0], "top5": res[:5], "default": default, "truth_cut_lines": len(cut_truth),
               "total_lines": len(cues)}, open(out, "w"), ensure_ascii=False, indent=1)
    print("기본값:", default)
    print(json.dumps(res[:5], ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:5])
