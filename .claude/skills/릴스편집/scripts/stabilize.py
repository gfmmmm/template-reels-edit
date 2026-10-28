#!/usr/bin/env python3
"""손떨림 보정(이동 보정) — ffmpeg deshake 가 아이폰 손떨림을 거의 못 줄여서(15.7→16.4px 실측) 직접 만든다.
shake_check.py 와 같은 방법(작게 줄인 프레임끼리 위상 상관)으로 프레임마다 화면 이동을 재고, 1초 이동 평균(의도한 움직임)을
따라가도록 남은 떨림만큼 화면을 반대로 옮긴다. 가장자리가 안 보이게 margin 만큼 확대한다(정답지 편집자: 흔들림 안정화, 최대 150%).

사용법: stabilize.py <입력 영상> <출력 영상> [--margin 0.08] [--smooth 1.0]
 margin: 위아래·좌우로 옮길 수 있는 여유(화면 비율). 클수록 더 잡지만 더 확대된다. 0.06~0.1
 smooth: 의도한 움직임으로 볼 이동 평균 길이(초). 걸어가며 찍은 장면은 크게(1.5)
출력: 같은 크기·같은 길이(프레임 수 그대로) 영상. 소리는 그대로 복사. 끝나면 shake_check.py 로 줄었는지 확인한다.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shake_check as sc  # noqa: E402


def arg(n, d):
    return float(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def main(src, out):
    margin, smooth = arg("--margin", 0.08), arg("--smooth", 1.0)
    fps = 30.0
    pos, w = sc.trajectory(src, fps)
    F, _ = sc.frames(src, fps, w)
    h = F.shape[1]
    corr = sc.smooth_path(pos, fps * smooth) - pos  # 이만큼 옮기면 의도한 움직임만 남는다 (줄인 프레임 px)
    cx = np.clip(corr[:, 0] / w, -margin / 2, margin / 2)  # 화면 비율
    cy = np.clip(corr[:, 1] / h, -margin / 2, margin / 2)
    sign = 1.0
    probe = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", "scale=iw:ih", "-frames:v", "1", "-f", "rawvideo",
                            "-pix_fmt", "gray", "-"], capture_output=True).stdout
    W = int(round((len(probe) / (h / w)) ** 0.5))  # 세워진 화면 폭 (회전 반영된 실제 프레임)
    H = len(probe) // W
    cw, ch = int(W * (1 - margin)) // 2 * 2, int(H * (1 - margin)) // 2 * 2
    cmd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    for i, (x, y) in enumerate(zip(cx, cy)):
        X = int(round((W - cw) / 2 - sign * x * W))
        Y = int(round((H - ch) / 2 - sign * y * H))
        cmd.write(f"{i / fps:.4f} crop@stab x {max(0, min(W - cw, X))}, crop@stab y {max(0, min(H - ch, Y))};\n")
    cmd.close()
    vf = f"fps=30,setpts=PTS-STARTPTS,sendcmd=f={cmd.name},crop@stab=w={cw}:h={ch}:x={(W - cw) // 2}:y={(H - ch) // 2},scale={W}:{H}"
    venc = (["-c:v", "hevc_videotoolbox", "-b:v", "20M", "-tag:v", "hvc1"] if sys.platform == "darwin"
            else ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf, *venc,
                    "-c:a", "copy", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out], check=True)
    os.unlink(cmd.name)
 # 확인: 보정 뒤 떨림이 10% 넘게 줄지 않으면(앞뒤 이동·회전 흔들림은 이동 보정으로 못 잡는다) 원본을 그대로 쓴다
    jit = lambda path: float(np.sqrt(((lambda pw: pw[0] - sc.smooth_path(pw[0], fps / 2))(sc.trajectory(path, fps)) ** 2).sum(axis=1)).mean())
    before, after = jit(src), jit(out) * (1 - margin)  # 확대한 만큼 떨림도 커 보이니 되돌려 비교
    if after > before * 0.9:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c", "copy", out], check=True)
        print(f"{os.path.basename(out)}: 보정해도 떨림이 안 줄어 원본 그대로 ({before:.1f} → {after:.1f}, 줄인 프레임 px)")
    else:
        print(f"{os.path.basename(out)}: 떨림 {before:.1f} → {after:.1f} ({(1 - after / before):.0%} 줄임), 여유 {margin:.0%}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
