#!/usr/bin/env python3
"""나레이션을 타임라인에 넣는다 — narration.py plan 뒤, 3단계 ③-A(화면 계획)보다 먼저.

사용법: narration_apply.py <결과폴더> [--clear]
입력: narration.json(dur·wav·words 채워진 것), timemap.json, spec.json, 편집본_단어시간.json, 편집본.srt, 타임라인.md, takes.json
하는 일:
 - 처음 돌릴 때 2단계 결과 다섯 파일을 narration/base/ 에 그대로 복사해 둔다. 그 뒤로는 언제나 base + narration.json 으로 다시 만든다
 (몇 번을 돌려도 같은 결과. --clear 는 base 로 되돌리고 나레이션 시간을 지운다).
 - hold: 그 문장이 끝난 자리에 정지 화면 조각(원본 마지막 프레임 png, 길이 = 나레이션 길이)을 끼우고 뒤 조각·단어·자막을 그만큼 민다.
 CapCut 에는 사진 조각(type photo), 미리보기에는 ffmpeg 정지 프레임으로 똑같이 들어간다.
 - over: 영상은 그대로, 그 시각(at)만 적는다. 그 구간에 원래 말이 있으면 경고.
 - 나레이션 소리: spec.json 에 "나레이션" 오디오 트랙(compile 이 CapCut 에 넣는다), 미리보기는 render_cut 이 섞는다.
 - 나레이션 단어는 편집본_단어시간.json 에 take=<id> 로 들어간다 → captions.py 자막, sync_check 대조에 그대로 쓰인다.
 - 끝에 render_cut.py 로 컷_미리보기.mp4 를 다시 만든다.
출력: timemap.json(hold 조각은 "hold": true, "png"), spec.json, 편집본_단어시간.json, 편집본.srt, 타임라인.md, narration.json(at 채움)
"""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["timemap.json", "spec.json", "편집본_단어시간.json", "편집본.srt", "타임라인.md"]
FR = 1 / 30


def srt_time(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def parse_srt(path):
    out = []
    for blk in re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip()):
        lines = blk.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        a = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        b = int(m[5]) * 3600 + int(m[6]) * 60 + int(m[7]) + int(m[8]) / 1000
        out.append([a, b, "\n".join(lines[2:])])
    return out


def write_srt(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, x) in enumerate(rows, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{x}\n\n")


def ensure_base(res):
    base = os.path.join(res, "narration", "base")
    if not os.path.isdir(base):
        os.makedirs(base)
        for f in FILES:
            if os.path.exists(os.path.join(res, f)):
                shutil.copy2(os.path.join(res, f), os.path.join(base, f))
    return base


def freeze_png(video, src_t, out):
    """원본의 src_t 시각 한 프레임을 1080×1920 png 로."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, src_t):.4f}", "-i", video, "-frames:v", "1",
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2", out], check=True)


def main(res, clear=False):
    res = os.path.abspath(res)
    base = ensure_base(res)
    segs = json.load(open(f"{base}/timemap.json", encoding="utf-8"))
    spec = json.load(open(f"{base}/spec.json", encoding="utf-8"))
    words = json.load(open(f"{base}/편집본_단어시간.json", encoding="utf-8"))
    srt = parse_srt(f"{base}/편집본.srt")
    timeline_md = open(f"{base}/타임라인.md", encoding="utf-8").read()
    video = spec["tracks"][0]["items"][0]["path"]
    video_abs = video if os.path.isabs(video) else os.path.join(res, video)  # cutplan 은 결과 폴더 기준 상대 경로를 쓰기도 한다
    np_ = os.path.join(res, "narration.json")
    items = [] if clear or not os.path.exists(np_) else json.load(open(np_, encoding="utf-8"))
    for it in items:
        if not (it.get("wav") and it.get("dur")):
            sys.exit(f"❌ {it.get('id')} 에 wav·dur 가 없어요 — 먼저 narration.py plan 을 돌려 주세요")

 # 문장 번호 → 그 문장의 마지막 조각 끝(기준 시간). 조각이 없는 번호는 오류
    def sentence_end(n):
        ss = [s for s in segs if s["take"] == n]
        if not ss:
            sys.exit(f"❌ after_sentence {n} 에 해당하는 문장이 timemap 에 없어요")
        return ss[-1]["start"] + ss[-1]["duration"], ss[-1]

    for it in items:
        it["_anchor"], it["_prev"] = sentence_end(it["after_sentence"])
    items.sort(key=lambda x: (x["_anchor"], 0 if x["mode"] == "hold" else 1))

    out_segs, out_words, out_srt = [dict(s) for s in segs], [dict(w) for w in words], [list(r) for r in srt]
    warn, offset, rows = [], 0.0, []
    for it in items:
        at = round(it["_anchor"] + offset, 4)
        if it["mode"] == "hold":
            d = round(max(FR, round(it["dur"] / FR) * FR), 4)  # 4자리로 맞춰야 뒤 조각 시각 비교가 어긋나지 않는다
            prev = it["_prev"]
            src_t = max(prev["src_in"], prev["src_out"] - prev["speed"] * FR)
            png = os.path.join(res, "narration", f"hold_{it['id']}.png")
            freeze_png(video_abs, src_t, png)
            hold = {"take": it["id"], "hold": True, "png": png, "src_in": round(src_t, 4), "src_out": round(src_t + FR, 4),
                    "speed": 1.0, "start": round(at, 4), "duration": round(d, 4), "continues": False, "narration": it["id"]}
 # 뒤 조각·단어·자막을 d 만큼 민다 (기준 시간 >= anchor 인 것)
            for s in out_segs:
                if s["start"] >= at - 1e-3 and not s.get("hold"):
                    s["start"] = round(s["start"] + d, 4)
                elif s.get("hold") and s["start"] >= at - 1e-3:
                    s["start"] = round(s["start"] + d, 4)
            for w in out_words:
                if w["s"] >= at - 1e-3:
                    w["s"], w["e"] = round(w["s"] + d, 3), round(w["e"] + d, 3)
            for r in out_srt:
                if r[0] >= at - 1e-3:
                    r[0], r[1] = r[0] + d, r[1] + d
            idx = next((k for k, s in enumerate(out_segs) if s["start"] > at + 1e-3), len(out_segs))
            out_segs.insert(idx, hold)
            offset += d
            it["at"], it["placed_dur"] = round(at, 4), round(d, 4)
        else:
            it["at"] = round(at, 4)
            clash = [w["w"] for w in out_words if w["s"] < at + it["dur"] - 0.05 and w["e"] > at + 0.05 and not str(w["take"]).startswith("n")]
            if clash:
                warn.append(f"{it['id']}(over) {at:.2f}~{at + it['dur']:.2f}초에 원래 말이 있어요: {' '.join(clash[:6])}{' …' if len(clash) > 6 else ''} → hold 로 바꾸거나 자리를 옮기세요")
        for w in it.get("words", []):
            out_words.append({"take": it["id"], "w": w["w"], "s": round(it["at"] + w["s"], 3), "e": round(it["at"] + w["e"], 3)})
        out_srt.append([it["at"], it["at"] + it["dur"], f"(나레이션) {it['text']}"])
        rows.append(f"| {it['id']} | {it['at']:.2f}~{it['at'] + it['dur']:.2f} | {'정지 화면' if it['mode'] == 'hold' else '얹음'} | 문장 {it['after_sentence']} 뒤 | {it['text']} |")

    if not items:  # 나레이션이 없으면 2단계 결과를 한 글자도 바꾸지 않고 되돌린다
        for f in FILES:
            if os.path.exists(f"{base}/{f}"):
                shutil.copy2(f"{base}/{f}", f"{res}/{f}")
        if os.path.exists(np_) and clear:
            js = json.load(open(np_, encoding="utf-8"))
            for it in js:
                it.pop("at", None)
                it.pop("placed_dur", None)
            json.dump(js, open(np_, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        subprocess.run([sys.executable, os.path.join(HERE, "render_cut.py"), res, video_abs], check=True)
        print(f"나레이션 없음 → 2단계 결과 그대로 ({segs[-1]['start'] + segs[-1]['duration']:.2f}초). 컷_미리보기 다시 만듦.")
        return
    t = round(out_segs[-1]["start"] + out_segs[-1]["duration"], 4)
    out_words.sort(key=lambda w: w["s"])
    out_srt.sort(key=lambda r: r[0])

    json.dump(out_segs, open(f"{res}/timemap.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    vitems = []
    for s in out_segs:
        if s.get("hold"):
            vitems.append({"path": s["png"], "type": "photo", "start": s["start"], "duration": s["duration"]})
        else:
            vitems.append({"path": video, "start": s["start"], "duration": s["duration"], "sourceStart": s["src_in"], "speed": s["speed"]})
    spec["tracks"] = [{"type": "video", "items": vitems}]
    if items:
        spec["tracks"].append({"type": "audio", "name": "나레이션", "items": [
            {"path": it["wav"], "start": it["at"], "duration": it["dur"], "volume": 1} for it in items]})
    json.dump(spec, open(f"{res}/spec.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(out_words, open(f"{res}/편집본_단어시간.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_srt(f"{res}/편집본.srt", out_srt)
    md = timeline_md.rstrip("\n")
    if rows:
        md += "\n\n## 나레이션\n\n| 번호 | 편집본 시간 | 방식 | 자리 | 문장 |\n|---|---|---|---|---|\n" + "\n".join(rows)
        md += f"\n\n나레이션 뒤 총 길이 {t:.2f}초 (정지 화면 +{offset:.2f}초)"
    open(f"{res}/타임라인.md", "w", encoding="utf-8").write(md + "\n")
    for it in items:
        it.pop("_anchor", None)
        it.pop("_prev", None)
    if items:
        json.dump(items, open(np_, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif os.path.exists(np_) and clear:
        js = json.load(open(np_, encoding="utf-8"))
        for it in js:
            it.pop("at", None)
            it.pop("placed_dur", None)
        json.dump(js, open(np_, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "render_cut.py"), res, video_abs], check=True)
    holds = [i for i in items if i["mode"] == "hold"]
    print(f"나레이션 {len(items)}개 반영 (정지 화면 {len(holds)}개 +{offset:.2f}초, 얹음 {len(items) - len(holds)}개) → 총 {t:.2f}초. "
          f"컷_미리보기 다시 만듦." + ("" if items else " (나레이션 없음 → 2단계 결과 그대로)"))
    for w in warn:
        print("⚠️", w)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a:
        sys.exit(__doc__)
    main(a[0], clear="--clear" in sys.argv)
