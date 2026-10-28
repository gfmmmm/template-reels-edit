#!/usr/bin/env python3
"""2단계 ③ 컷 설계도 — 고른 테이크 → 남길 조각 → compile 설계도·편집본 기준 시간.

사용법: cutplan.py <결과폴더> <편집용 영상> [--th -30 --ms 0.15 --pad 0.03 --lead 0.04 --tail 0.1 --min-gap 0.15 --fast 9.5]
기본값은 무음을 타이트하게. 끝소리가 잘리면 그 문장만 edge_fix.json으로 늘린다.
입력: <결과폴더>/takes.json [[번호, 교정 문장, 덩어리 번호([첫 단어, 끝 단어])], ...]
 <결과폴더>/speed.json(있으면) {"문장번호": 1.0} — AI가 정한 문장별 배속. 공용 규칙: 기본 1.1배, 말이 이미 빠른 문장은 1.0배, 1.2배 이상은 너무 루즈한 구간에서만
 <결과폴더>/stt_chunks/chunks.json (transcribe_chunks.py 결과)
출력: spec.json(compile 설계도), timemap.json(편집본 시간 ↔ 원본 시간),
 편집본_단어시간.json, 편집본.srt(문장 단위), 타임라인.md(사람이 보는 표)
규칙: 테이크 안의 쉬는 틈은 detect-silence(메뉴얼 13번 값)로 자르고, 조각마다 단어 앞뒤 여유를 둔다.
 speed.json에 없는 문장: 말 속도(쉰 틈 뺀 1초당 글자)가 --fast 이상이면 1.0배, 아니면 1.1배.
"""
import json
import os
import subprocess
import sys
import tempfile


def arg(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def keeps(video, th, ms, pad):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:  # 파이프는 64KB에서 잘린다
        subprocess.run(["capcut", "detect-silence", video, "--threshold-db", str(th),
                        "--min-silence", str(ms), "--pad", str(pad)], stdout=fh)
    k = json.load(open(tmp))["keeps"]
    os.unlink(tmp)
    return [(x["start"], x["end"]) for x in k]


def srt_time(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


# 무음 자르기 기준의 하한 — 이보다 조이지 않는다. 길이를 맞추려고 조이면 문장 안 짧은 쉼까지 잘려
# "받을|수 있는"처럼 말 한가운데서 화면이 튀고 0.4초 조각이 생긴다(IMG_0519, 사용자 "컷편집 왜 저래").
# 길이는 테이크 바꾸기·문장 빼기·배속으로 맞추고, 그래도 넘치면 넘긴 채 보고한다(2_컷편집.md ②).
FLOOR = {"--pad": 0.03, "--ms": 0.15, "--min-gap": 0.15, "--lead": 0.04, "--tail": 0.1}
for _k, _v in FLOOR.items():
    if _k in sys.argv and float(sys.argv[sys.argv.index(_k) + 1]) < _v:
        print(f"{_k} {sys.argv[sys.argv.index(_k) + 1]}은 하한 {_v}보다 타이트해서 {_v}로 씁니다 (길이는 다른 방법으로 맞출 것)")
        sys.argv[sys.argv.index(_k) + 1] = str(_v)


def main(res, video):
    th, ms, pad, fast = arg("--th", -30), arg("--ms", 0.15), arg("--pad", 0.03), arg("--fast", 8.5)
    takes = json.load(open(f"{res}/takes.json"))
    speeds = json.load(open(f"{res}/speed.json")) if os.path.exists(f"{res}/speed.json") else {}
    chunks = {c["i"]: c for c in json.load(open(f"{res}/stt_chunks/chunks.json"))}
    edge_fix = json.load(open(f"{res}/edge_fix.json")) if os.path.exists(f"{res}/edge_fix.json") else {}
    inner_cuts = json.load(open(f"{res}/inner_cuts.json")) if os.path.exists(f"{res}/inner_cuts.json") else {}
 # 통화·스피커 소리처럼 작게 녹음된 문장은 무음 자르기에서 말이 빠진다 → nocut.json [문장번호, ...]은 통째로 둔다
    nocut = set(json.load(open(f"{res}/nocut.json"))) if os.path.exists(f"{res}/nocut.json") else set()
    K = keeps(video, th, ms, pad)
    segs, words_out, srt, t = [], [], [], 0.0
 # 인트로(계정 메뉴얼이 정할 때만): 첫 말 앞 말 없는 행동 장면을 빠르게 맨 앞에 — intro.json {"src": [원본 시작, 끝], "speed": 2.0}
 # 문장 번호 0(글자 없음)으로 넣는다. 자막은 없고(captions 는 takes 만 본다) 3단계에서 상황 메모·휘익을 얹는다(정답지).
    if os.path.exists(f"{res}/intro.json"):
        it = json.load(open(f"{res}/intro.json"))
        ia, ib = it["src"]
        isp = float(it.get("speed", 2.0))
        fr = 1 / 30
        idur = max(fr, round((ib - ia) / isp / fr) * fr)
        segs.append({"take": 0, "src_in": round(ia, 4), "src_out": round(ia + idur * isp, 4), "speed": isp,
                     "start": 0.0, "duration": round(idur, 4), "continues": False})
        t = idur
    for tk in takes:
        n, text, ci = tk[:3]
        c = chunks[ci]
        w = c["words"]
        nxt_s = None
        if len(tk) > 3 and tk[3]:  # 여러 문장을 이어 말한 덩어리에서 이 문장 부분만
            a_, b_ = tk[3]
            nxt_s = w[b_ + 1]["s"] if b_ + 1 < len(w) else None
            w = w[a_:b_ + 1]
 # 받아쓰기 단어 끝은 실제보다 일찍 찍히는 경향 → 말끝은 덩어리 끝(말 끝+0.1초)까지 조금 더 남긴다
        lo = w[0]["s"] - arg("--lead", 0.04)
        hi = min(c["end"] - 0.03, w[-1]["e"] + arg("--tail", 0.1))
        if tk is takes[-1]:  # 영상 마지막 말은 끝소리가 잘리지 않게 여유를 더 둔다(사용자: 끝말이 잘림)
            hi = w[-1]["e"] + arg("--last-tail", 0.45)
        if nxt_s is not None:  # 다음 문장 첫 단어가 들리지 않게
            hi = min(hi, nxt_s - 0.03)
        pieces = [(max(a, lo), min(b, hi)) for a, b in K if min(b, hi) - max(a, lo) >= 0.12]
 # 문장 안의 아주 짧은 쉼(--min-gap 미만)은 자르지 않는다 — 시간은 거의 안 줄고 화면만 툭 튄다
        merged = []
        for a, b in pieces:
            if merged and a - merged[-1][1] < arg("--min-gap", 0.15):
                merged[-1] = (merged[-1][0], b)
            else:
                merged.append((a, b))
        pieces = merged
 # 문장 안 숨 자르기: inner_cuts.json {"문장번호": [[원본 시작, 원본 끝], ...]} — 무음 기준(-30dB)보다 큰 숨소리처럼
 # detect-silence가 못 자르는 쉼. suspect_check의 "숨 쉼" 후보(받아쓰기 단어 경계에 있는 것만)나 사용자가 짚은 곳만.
 # 단어 안(받침 닫힘 'ㄱ·ㄷ' 순간)을 자르면 말이 씹힌다(IMG_0519) → 0.25초 안 되는 조각이 생기면 안 자른다.
        for ca, cb in inner_cuts.get(str(n), []):
            nxt = []
            for a, b in pieces:
                if a < ca and cb < b and ca - a >= 0.25 and b - cb >= 0.25:
                    nxt += [(a, ca), (cb, b)]
                else:
                    nxt.append((a, b))
            pieces = nxt
        if n in nocut:
            pieces = [(lo, hi)]
        if not pieces:
            pieces = [(lo, hi)]
 # 검수가 잰 말끝 꼬리·첫머리 보정: edge_fix.json {"문장번호": {"start": 원본초, "end": 원본초}}
        fx = edge_fix.get(str(n), {})
        if "start" in fx:  # 새 시작보다 먼저 끝나는 조각(앞 문장 꼬리·잡음)은 버리고, 남은 첫 조각의 시작을 옮긴다
            keep_p = [(a, b) for a, b in pieces if b > fx["start"] + 0.05] or [(fx["start"], pieces[-1][1])]
            pieces = [(fx["start"], keep_p[0][1])] + keep_p[1:]
        if "end" in fx:  # 새 끝보다 늦게 시작하는 조각은 버리고, 남은 마지막 조각의 끝을 옮긴다
            keep_p = [(a, b) for a, b in pieces if a < fx["end"] - 0.05] or [(pieces[0][0], fx["end"])]
            pieces = keep_p[:-1] + [(keep_p[-1][0], fx["end"])]
        speech = sum(b - a for a, b in pieces)
        cps = len(text.replace(" ", "").replace(",", "")) / speech
        speed = float(speeds[str(n)]) if str(n) in speeds else (1.0 if cps >= fast else 1.1)
 # 긴 조각은 단어 경계에서 나눈다 (점프컷·확대 자리). 첫 컷은 더 짧게(메뉴얼 2번)
        split = []
        for a, b in pieces:
            limit = (arg("--first-max", 1.9) if not segs and not split else arg("--max-piece", 2.5)) * speed
            while b - a > limit:
                cands = [x["e"] for x in w if a + 0.8 * speed < x["e"] < a + limit - 0.1]
                if not cands:
                    break
                cut = cands[-1]
                split.append((a, cut, True))
                a = cut
                limit = arg("--max-piece", 2.5) * speed
            split.append((a, b, False))
        sent_start = t
        mine, prev_b = [], None
        for a, b, cont in split:
            if prev_b is not None:  # 문장 안에서 나눈 곳은 앞 조각 끝 = 뒤 조각 시작 (겹침·빈틈 0)
                a = prev_b
            fr = 1 / 30  # CapCut·미리보기 모두 프레임 단위 → 편집본 길이를 프레임에 맞춘다
            dur = max(fr, round((b - a) / speed / fr) * fr)
            b = a + dur * speed
            seg = {"take": n, "src_in": round(a, 4), "src_out": round(b, 4), "speed": speed,
                   "start": round(t, 4), "duration": round(dur, 4), "continues": cont}
            segs.append(seg)
            mine.append(seg)
            prev_b = b if cont else None
            t += dur

        def to_edit(x):  # 원본 시각 → 편집본 시각 (조각 밖이면 가장 가까운 조각 끝으로)
            for s in mine:
                if s["src_in"] <= x <= s["src_out"]:
                    return s["start"] + (x - s["src_in"]) / s["speed"]
            near = min(mine, key=lambda s: min(abs(x - s["src_in"]), abs(x - s["src_out"])))
            return near["start"] if x < near["src_in"] else near["start"] + near["duration"]

        for x in w:  # 단어는 한 번만, 시작이 속한 자리에 넣는다
            s_, e_ = to_edit(x["s"]), to_edit(x["e"])
            if e_ - s_ > 0.005:
                words_out.append({"take": n, "w": x["w"], "s": round(s_, 3), "e": round(e_, 3)})
        srt.append((sent_start, t, text))
    json.dump({"name": os.path.basename(os.path.abspath(res)), "width": 1080, "height": 1920, "fps": 30, "ratio": "9:16",
               "tracks": [{"type": "video", "items": [
                   {"path": video, "start": s["start"], "duration": s["duration"],
                    "sourceStart": s["src_in"], "speed": s["speed"]} for s in segs]}]},
              open(f"{res}/spec.json", "w"), ensure_ascii=False, indent=1)
    json.dump(segs, open(f"{res}/timemap.json", "w"), ensure_ascii=False, indent=1)
    json.dump(words_out, open(f"{res}/편집본_단어시간.json", "w"), ensure_ascii=False, indent=1)
    with open(f"{res}/편집본.srt", "w") as f:
        for i, (a, b, x) in enumerate(srt, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{x}\n\n")
    L = ["| 문장 | 편집본 시간 | 원본 시간 | 조각 수 | 배속 | 문장 |", "|---|---|---|---|---|---|"]
    for tk in takes:
        n, text = tk[0], tk[1]
        ss = [s for s in segs if s["take"] == n]
        L.append(f"| {n} | {ss[0]['start']:.2f}~{ss[-1]['start'] + ss[-1]['duration']:.2f} | "
                 f"IMG {ss[0]['src_in']:.2f}~{ss[-1]['src_out']:.2f} | {len(ss)} | {ss[0]['speed']} | {text} |")
    durs = [s["duration"] for s in segs]
    L += ["", f"총 길이 {t:.2f}초, 조각 {len(segs)}개, 조각 평균 {sum(durs) / len(durs):.2f}초"]
    open(f"{res}/타임라인.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[-1:]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
