#!/usr/bin/env python3
"""3단계 ③-A 3-0 J컷 — 새 말하는 장면 첫머리에 인물이 걸어 들어오는 중이거나 얼굴이 화면 끝에 잘려 있으면,
목소리는 그대로 두고 그림만 앞 장면을 0.3~0.6초 더 붙잡는다(공용 규칙 60).
(한 생활용품 계정 게시본 대조: 스킬은 질문 뒤 첫 대답에서 인물이 화면에 막 들어오는 0.5초를 그대로 보여 줬고,
 편집자는 질문 장면을 0.6초 더 붙잡은 뒤 자리 잡은 인물로 넘어갔다. 평가 "첫 3초 컷이 어색하다" 1순위)

사용법: jcut.py <결과폴더> [--max 0.6] [--min 0.3] (render_cut.py → face_anchor.py 다음, screen_clip.py 전에)
쓰는 때: 말 영상이 여럿이거나(대사마다 파일) 인물이 화면 밖에서 들어오는 촬영 — 계정 메뉴얼이 켤 때만(rebuild.sh --jcut). 한 자리 원테이크
토킹헤드는 앞 조각 뒤가 다음 테이크 얼굴이라 멈춘 얼굴이 생길 수 있어 쓰지 않는다(공용 60 충돌 점검).
입력: timemap.json, broll-plan.json, screens.json, zoom.json, faces.json, overlays.json(있으면), preview/컷_미리보기.mp4, spec.json(말 영상 경로)
판정: 문장이 바뀌는 말 조각(원본이 이어지지 않음)마다 컷 미리보기의 첫 0.05·0.25·0.45초 장면에서 얼굴을 찾는다.
 첫 장면에 얼굴이 없는데 뒤에서 나타나거나, 얼굴이 화면 끝(가로 15%·85% 바깥, 위 10% 안)에 걸려 있거나, 0.4초 사이 얼굴이
 화면 8% 넘게 움직이면(걸어 들어옴) "들어오는 중". 얼굴이 화면 안쪽에 처음 들어온 때까지(0.3~0.6초) 앞 조각을 이어 보여 주는 카드를 만든다.
카드: screens.json·broll-plan.json 에 "jcut-<조각번호>"(role "jcut") — 앞 조각 원본의 뒷부분, 앞 조각과 같은 확대·위치.
 앞 조각 원본 뒤에도 인물이 들어오는 게 보이면(얼굴이 잡히면) 앞 조각 마지막 장면을 멈춘 사진으로 대신한다.
 그 사이에 메모가 뜨면 끝 배율만 +0.1(반응 순간 살짝 다가가기). 다시 돌리면 jcut-* 카드를 지우고 새로 만든다 —
 손으로 고친 J컷은 카드에 "keep": true 를 붙이면 그대로 두고, 손으로 지운 자리는 broll-plan.json "jcut_off": [조각번호] 에 적으면
 다시 만들지 않는다(블라인드 시험: 검수가 지운 J컷이 다음 rebuild 에서 되살아났다).
 원본이 0.2초 안으로 거의 이어지는 경계는 인물이 들어오는 컷이 아니라 J컷을 만들지 않는다(같은 파일이 0.06초 만에 이어지는 경계에
 멈춘 사진 0.3초가 끼어 0.27초 인물 조각이 툭 튀었다).
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402
from build_spec import focus_anchor  # noqa: E402


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def frame(video, t, out):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1",
                    "-vf", "scale=540:-2", out], check=True)
    return out


def main(res):
    mx, mn = arg("--max", 0.6), arg("--min", 0.3)
    tm = json.load(open(f"{res}/timemap.json"))
    plan = json.load(open(f"{res}/broll-plan.json"))
    S = json.load(open(f"{res}/screens.json")) if os.path.exists(f"{res}/screens.json") else []
    L = S if isinstance(S, list) else S["screens"]
    zoom = json.load(open(f"{res}/zoom.json")) if os.path.exists(f"{res}/zoom.json") else {}
    faces = focus_anchor(zoom, json.load(open(f"{res}/faces.json")))
    ovs = json.load(open(f"{res}/overlays.json")) if os.path.exists(f"{res}/overlays.json") else []
    talk = json.load(open(f"{res}/spec.json"))["tracks"][0]["items"][0]["path"]
    talk = talk if os.path.isabs(talk) else os.path.abspath(os.path.join(res, talk))
    prev_mp4 = f"{res}/preview/컷_미리보기.mp4"
    kept = {c["id"] for c in plan["cards"] if c.get("role") == "jcut" and c.get("keep")}
    plan["cards"] = [c for c in plan["cards"] if c.get("role") != "jcut" or c["id"] in kept]
    L[:] = [s for s in L if not str(s.get("id", "")).startswith("jcut-") or s.get("id") in kept]
    off = {int(x) for x in plan.get("jcut_off", [])}
    tmp = tempfile.mkdtemp()
    made = []
    for j in range(1, len(tm)):
        p, s = tm[j - 1], tm[j]
        if s["take"] == p["take"] or abs(s["src_in"] - p["src_out"]) < 0.2 or j in off or f"jcut-{j}" in kept:
            continue  # 문장이 바뀌고 원본이 끊기는 컷만(거의 이어지는 경계·끈 자리·손으로 고친 자리는 빼고)
        t0 = s["start"]
        if any(c["start"] - 0.01 <= t0 < c["end"] for c in plan["cards"]):
            continue  # 이미 자료화면이 덮는다
        if any(c["start"] - 0.01 <= t0 - 0.05 < c["end"] for c in plan["cards"]):
            continue  # 앞 조각 끝이 자료화면이면 이어 붙잡을 그림이 없다
        offs = [0.05, 0.25, 0.45, 0.65]
        offs = [o for o in offs if o < s["duration"]]
        got = pu.face_centers([frame(prev_mp4, t0 + o, f"{tmp}/{j}_{k}.jpg") for k, o in enumerate(offs)])
        first = got[0] if got else None
        inside = lambda g: g is not None and 0.15 <= g[0] <= 0.85 and g[1] >= 0.1  # noqa: E731
        moving = first is not None and len(got) > 2 and got[2] is not None and \
            ((got[2][0] - first[0]) ** 2 + (got[2][1] - first[1]) ** 2) ** 0.5 > 0.08
        entering = (first is None and any(g is not None for g in got[1:])) or \
                   (first is not None and not inside(first)) or moving
        if not entering:
            continue
        settle = next((o for o, g in zip(offs, got) if inside(g)), mx)
        dur = round(round(min(mx, max(mn, settle)) * 30) / 30, 4)
        sc = float(zoom.get("scales", {}).get(str(j - 1), 1.0))
        ax, ay = faces.get(str(j - 1), [0.5, 0.5])
        pos = [round(2 * (sc - 1) * (0.5 - ax), 3), round(-2 * (sc - 1) * (0.5 - ay), 3)]
        react = any(t0 - 0.05 <= o["start"] < t0 + dur for o in ovs)
        sc1 = round(sc + 0.1, 3) if react else sc
 # 앞 조각 원본의 뒷부분에도 인물이 들어오면(얼굴이 잡히면) 멈춘 사진으로
        cont = pu.face_centers([frame(talk, p["src_out"] + o, f"{tmp}/c{j}_{k}.jpg") for k, o in enumerate([0.1, dur])])
        cid = f"jcut-{j}"
        if any(g is not None for g in cont):
            png = os.path.join(res, "captures", f"{cid}.png")
            os.makedirs(os.path.dirname(png), exist_ok=True)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{p['src_out'] - 0.04:.3f}", "-i", talk,
                            "-frames:v", "1", png], check=True)
            layer = {"src": png, "freeze": True, "scale": [sc, sc1], "pos": [pos, pos]}
            how = "앞 장면 멈춤"
        else:
            layer = {"src": talk, "in": round(p["src_out"], 3), "speed": 1.0, "scale": [sc, sc1], "pos": [pos, pos]}
            how = "앞 장면 이어서"
        L.append({"id": cid, "start": 0, "end": dur, "bg": "#000000", "layers": [layer]})
        plan["cards"].append({"id": cid, "component": "Screen", "role": "jcut", "start": round(t0, 4), "end": round(t0 + dur, 4),
                              "props": {}, "reason": f"J컷 — 새 장면 첫머리에 인물이 들어오는 중({how})"})
        made.append((cid, round(t0, 2), dur, how))
    plan["cards"].sort(key=lambda c: c["start"])
    json.dump(plan, open(f"{res}/broll-plan.json", "w"), ensure_ascii=False, indent=1)
    json.dump(S, open(f"{res}/screens.json", "w"), ensure_ascii=False, indent=1)
    for m in made:
        print(*m)
    print(f"J컷 {len(made)}곳 → screens.json·broll-plan.json (screen_clip.py 로 카드를 만든다)")


if __name__ == "__main__":
    main(sys.argv[1])
