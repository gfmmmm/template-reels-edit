#!/usr/bin/env python3
"""3단계 검수용 확인본 — 컷·배속·확대·자료화면 카드·자막·상단 제목·효과음을 ffmpeg로 합친다.
(capcut render는 카드·확대·자막을 못 보여 준다. 장면 전환 효과만 빠진다.)

사용법: render_check.py <결과폴더> <자막 레이어.mov> [--scale 0.5]
입력: timemap.json, spec.json(편집용 영상 경로), zoom.json(scales·first_punch·punch_at·ramps), broll-plan.json + cards/*.mov(화면녹화 클립 포함), sfx-plan.json
자막 레이어: Remotion overlay-any 컴포지션(--props=preview/overlay_props.json)을 투명 ProRes로 렌더한 것. --scale 1이면 preview/최종본_고화질.mp4(승인용)
출력: preview/확인본.mp4
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



def focus_anchor(zoom, faces):
    """zoom.json "focus": {"조각번호": [x, y]} — 얼굴 대신 손·제품 같은 부분을 확대할 때(디테일 확대, 2026-10-26 정답지 대조).
    그 점(0~1, 화면 비율)이 확대 뒤 화면 가운데로 오게 하는 기준점으로 바꿔 faces 를 덮는다(화면 밖이 보이지 않게 0~1로 자름)."""
    out = dict(faces)
    for i, (fx, fy) in zoom.get("focus", {}).items():
        s = float(zoom["scales"].get(str(i), 1.0))
        if s <= 1.0:
            continue
        cl = lambda v: max(0.0, min(1.0, v))
        out[str(i)] = [round(cl((fx * s - 0.5) / (s - 1)), 4), round(cl((fy * s - 0.5) / (s - 1)), 4)]
    return out

def main(res, overlay, scale=0.5):
    segs = json.load(open(f"{res}/timemap.json"))
    video = json.load(open(f"{res}/spec.json"))["tracks"][0]["items"][0]["path"]
    zoom = json.load(open(f"{res}/zoom.json"))
    cards = json.load(open(f"{res}/broll-plan.json"))["cards"]
    sfx = json.load(open(f"{res}/sfx-plan.json"))["keep"]
    rows = {r["template"].split("/")[-1].replace(".json", ""): r for r in json.load(open(f"{SKILL}/sfx/palette_heard.json"))}
    W, H = int(1080 * scale), int(1920 * scale)
    end = segs[-1]["start"] + segs[-1]["duration"]
    inputs = ["-i", video, "-i", overlay]
    fc, vparts = [], []
 # 확대 기준점 = 얼굴(faces.json). 없으면 화면 가운데
    faces = json.load(open(f"{res}/faces.json")) if os.path.exists(f"{res}/faces.json") else {}
    faces = focus_anchor(zoom, faces)
    for i, s in enumerate(segs):
        fx, fy = faces.get(str(i), [0.5, 0.5])
        z = zoom["scales"].get(str(i), 1.0)
        fp = zoom.get("first_punch") if i == 0 else None
        nf = max(1, int(round(s["duration"] * 30)))
        if fp:
            k = int(fp[1] * 30)
            tail = f"1+({fp[2]}-1)*(on-{k})/{max(1, nf - k)}" if len(fp) > 2 else "1"
            zexpr = f"if(lte(on,{k}),{fp[0]}-({fp[0]}-1)*on/{k},{tail})"
        elif str(i) in zoom.get("ramps", {}):
            a, b = zoom["ramps"][str(i)]
            zexpr = f"{a}+({b}-{a})*on/{nf}"
        else:
            zexpr = str(z)
        for t, sc in sorted(zoom.get("punch_at", [])):  # 계단식: 이른 것부터 감싼다 → 늦은 시점일수록 바깥 조건
            if s["start"] <= t < s["start"] + s["duration"]:
                zexpr = f"if(lt(on,{int(round((t - s['start']) * 30))}),{zexpr},{sc})"
 # zoompan은 천천히 확대할 때 정수 좌표로 반올림돼 화면이 떨린다(사용자 지적) → 2배 크기에서 매 프레임 확대 후 가운데 잘라 줄인다
        zx = zexpr.replace("on", "(t*30)")  # scale 필터의 n은 프레임마다 갱신되지 않는다(천천히 확대가 계단처럼 튐) → t로
        if s.get("hold"):  # 나레이션 정지 화면: 한 프레임을 멈춰 보여 준다
            src = pu.hold_video_filter(s["src_in"], s["duration"])
        else:
            src = (f"[0:v]trim={s['src_in']}:{s['src_out'] + 0.1},setpts=(PTS-STARTPTS)/{s['speed']},fps=30,"
                   f"trim=duration={s['duration']},setpts=PTS-STARTPTS")
        fc.append(src + ","
                  f"scale=w='trunc({2 * W}*({zx})/2)*2':h=-2:eval=frame:flags=bicubic,"
                  f"crop={2 * W}:{2 * H}:(iw-{2 * W})*{fx}:(ih-{2 * H})*{fy},scale={W}:{H}:flags=area,setsar=1[v{i}]")
        vparts.append(f"[v{i}]")
    fc.append("".join(vparts) + f"concat=n={len(segs)}:v=1:a=0[base]")
 # 소리: 같은 배속끼리 이어 붙인 뒤 배속은 한 번만
    groups = []
    AF = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    for i, s in enumerate(segs):
        if s.get("hold"):  # 정지 화면 구간은 무음(나레이션은 아래서 섞는다)
            groups.append({"sp": None, "idx": [i], "hold": s["duration"]})
        elif groups and groups[-1]["sp"] == s["speed"]:
            groups[-1]["idx"].append(i)
        else:
            groups.append({"sp": s["speed"], "idx": [i]})
    gp = []
    for g, grp in enumerate(groups):
        if grp.get("hold"):
            fc.append(f"aevalsrc=0:d={grp['hold']}:s=48000:c=stereo,{AF}[g{g}]")
            gp.append(f"[g{g}]")
            continue
        for i in grp["idx"]:
            fc.append(f"[0:a]atrim={segs[i]['src_in']}:{segs[i]['src_out']},asetpts=PTS-STARTPTS[r{i}]")
        d = sum(segs[i]["duration"] for i in grp["idx"])
 # 배속은 원본 길이 ÷ 화면 길이로 다시 잰다 — 조각 길이를 프레임 단위로 반올림해서 이름표 배속(1.1)으로 줄이면 소리가 조금 짧아져
 # 묶음 끝에 완전 무음이 생겼다(블라인드 시험: 배속이 바뀌는 이음에 26ms 무음, 방 소리가 툭 끊김)
        src_len = sum(segs[i]["src_out"] - segs[i]["src_in"] for i in grp["idx"])
        tempo = round(min(2.0, max(0.5, src_len / d)), 5) if d > 0 else grp["sp"]
        fc.append("".join(f"[r{i}]" for i in grp["idx"]) + f"concat=n={len(grp['idx'])}:v=0:a=1,atempo={tempo},"
                  f"apad,atrim=duration={d},asetpts=PTS-STARTPTS,{AF}[g{g}]")
        gp.append(f"[g{g}]")
    fc.append("".join(gp) + f"concat=n={len(groups)}:v=0:a=1[voice0]")
 # 카드
    last = "base"
    n_in = 2
    for k, c in enumerate(cards):
        inputs += ["-i", f"{res}/cards/{c['id']}.mov"]
 # 시작은 프레임 번호로(소수 반올림 때문에 첫 프레임이 늦게 붙으면 인물이 1프레임 비친다)
 # 반 프레임 앞당겨 붙인다: 같은 시각이면 소수 반올림으로 카드 첫 프레임이 한 프레임 늦게 잡혀 인물이 비친다
        fc.append(f"[{n_in}:v]scale={W}:{H},setpts=PTS-STARTPTS+({int(round(c['start'] * 30))}-0.5)/30/TB[c{k}]")
 # eof_action=pass는 카드 마지막 프레임을 버려 이음마다 인물이 1프레임 비친다 → repeat + 구간 제한
        fc.append(f"[{last}][c{k}]overlay=0:0:eof_action=repeat:enable='between(t,{c['start'] - 0.5 / 30},{c['end'] - 0.5 / 30})'[o{k}]")
        last = f"o{k}"
        n_in += 1
    fc.append(f"[1:v]scale={W}:{H}[ov]")
    fc.append(f"[{last}][ov]overlay=0:0:eof_action=pass,trim=duration={end}[vout]")
 # 나레이션(있으면 그 시각에 섞는다) → 효과음
    n_in = pu.narration_mix(inputs, fc, n_in, "voice0", res, "voice")
    ap = ["[voice]"]
    for k, x in enumerate(sfx):
        r = rows[x["template"].split("/")[-1].replace(".json", "")]
        src = r["copy"] if os.path.isabs(r["copy"]) else os.path.join(SKILL, "sfx", r["copy"])  # 이식본은 sfx/ 기준 상대 경로(files/NN.mp3)
        inputs += ["-i", src]
        ms = int(x["place"] * 1000)
        fc.append(f"[{n_in}:a]atrim=0:{x['dur']},asetpts=PTS-STARTPTS,volume={x['volume']},"
                  f"aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[s{k}]")
        ap.append(f"[s{k}]")
        n_in += 1
 # 승인용 그림도 최고점 -1.5dB 아래로(문장 크기 고르기로 키운 말 + 효과음이 -0.6~-0.9dB 까지 올라 기준 -1 을 넘었다).
 # 업로드용은 4단계 finish_audio 가 따로 맞춘다
    fc.append("".join(ap) + f"amix=inputs={len(ap)}:normalize=0:duration=first,alimiter=limit=0.82:attack=3:release=60:level=0[aout]")
    os.makedirs(f"{res}/preview", exist_ok=True)
    script = f"{res}/preview/.check_filter.txt"
    open(script, "w").write(";\n".join(fc))
    out = f"{res}/preview/" + ("최종본_고화질.mp4" if scale >= 1 else "확인본.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-/filter_complex", script, "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "slow" if scale >= 1 else "veryfast", "-crf", "16" if scale >= 1 else "22", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
    os.remove(script)
    print(out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sc = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 0.5
    a = [x for x in a if x != str(sc)]
    main(a[0], a[1], sc)
