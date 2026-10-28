#!/usr/bin/env python3
"""컷 미리보기 — timemap.json대로 조각을 이어 붙인 확인용 영상(CapCut 없이 ffmpeg로).
2단계에서 실제 소리로 틈·말 잘림을 재고, compile 결과와 비교하는 기준본으로 쓴다.

사용법: render_cut.py <결과폴더> <편집용 영상> [출력.mp4] [--scale 0.5]
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def main(res, video, out=None, scale=0.5):
    segs = json.load(open(f"{res}/timemap.json"))
    out = out or f"{res}/preview/컷_미리보기.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fc, vparts, groups = [], [], []
    for i, s in enumerate(segs):
        sp = s["speed"]
        d = s["duration"]  # 조각마다 영상 길이를 설계도와 똑같이
        if s.get("hold"):  # 나레이션 정지 화면: 한 프레임을 멈춰 보여 주고 소리는 무음(나레이션은 뒤에서 섞는다)
            fc.append(pu.hold_video_filter(s["src_in"], d) + f",scale=iw*{scale}:ih*{scale}[v{i}]")
            vparts.append(f"[v{i}]")
            groups.append({"speed": None, "idx": [i], "hold": d})
            continue
        fc.append(f"[0:v]trim={s['src_in']}:{s['src_out'] + 0.1},setpts=(PTS-STARTPTS)/{sp},"
                  f"fps=30,trim=duration={d},setpts=PTS-STARTPTS,scale=iw*{scale}:ih*{scale}[v{i}]")
        vparts.append(f"[v{i}]")
        if groups and groups[-1]["speed"] == sp:
            groups[-1]["idx"].append(i)
        else:
            groups.append({"speed": sp, "idx": [i]})
    fc.append("".join(vparts) + f"concat=n={len(segs)}:v=1:a=0[v]")
 # 소리: 배속이 같은 조각끼리 먼저 이어 붙이고 배속은 한 번만 건다
 # (조각마다 atempo를 걸면 이음마다 25~45ms 무음이 생긴다)
    gparts = []
    AF = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    for g, grp in enumerate(groups):
        if grp.get("hold"):
            fc.append(f"aevalsrc=0:d={grp['hold']}:s=48000:c=stereo,{AF}[g{g}]")
            gparts.append(f"[g{g}]")
            continue
        for i in grp["idx"]:
            s = segs[i]
            fc.append(f"[0:a]atrim={s['src_in']}:{s['src_out']},asetpts=PTS-STARTPTS[r{i}]")
        d = sum(segs[i]["duration"] for i in grp["idx"])
        fc.append("".join(f"[r{i}]" for i in grp["idx"]) + f"concat=n={len(grp['idx'])}:v=0:a=1,"
                  f"atempo={grp['speed']},apad,atrim=duration={d},asetpts=PTS-STARTPTS,{AF}[g{g}]")
        gparts.append(f"[g{g}]")
    fc.append("".join(gparts) + f"concat=n={len(groups)}:v=0:a=1[voice]")
    inputs = ["-i", video]
    pu.narration_mix(inputs, fc, 1, "voice", res, "a")  # 나레이션이 있으면 그 시각에 섞는다(없으면 그대로)
    script = f"{res}/preview/.filter.txt"
    open(script, "w").write(";\n".join(fc))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-/filter_complex", script,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "160k", out], check=True)
    os.remove(script)
    print(out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sc = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 0.5
    a = [x for x in a if x != str(sc)]
    main(a[0], a[1], a[2] if len(a) > 2 else None, sc)
