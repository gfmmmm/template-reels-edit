#!/usr/bin/env python3
"""컴퓨터별로 다른 도구를 한 곳에서 고르는 공통 모듈 — 맥(애플칩·인텔)과 윈도우에서 같은 스크립트가 돌게 한다.
(윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.)

다른 스크립트는 `import platform_util as pu` 로 불러 쓴다.
 pu.os_kind "mac" | "win" | "other"
 pu.capcut_running CapCut 앱이 켜져 있으면 True
 pu.transcribe(wav, ...) 받아쓰기. 맥 애플칩은 mlx_whisper, 그 외는 faster_whisper(또는 whisper-ctranslate2)
 결과 모양은 늘 같다: {"text", "segments": [{"text", "start", "end", "words": [{"word", "start", "end"}]}]}
 pu.hdr_to_sdr(src, dst) HDR 영상을 SDR로. 맥은 avconvert, 그 외는 ffmpeg zscale
 pu.video_encoder_args 영상을 다시 압축할 때 쓰는 ffmpeg 인코더 인자
 pu.face_centers(jpg_paths) 사진마다 얼굴 가운데 [fx, fy](0~1) 또는 None. 맥은 Vision, 그 외는 opencv
 pu.person_matte(in_mp4, out_mov) 인물만 오려낸 투명 영상. 맥은 Vision, 그 외는 rembg. 못 하면 False
 pu.remotion_dir 환경.md 의 [Remotion폴더] (없으면 ~/Projects/reels-edit-remotion)
 pu.env_value("[이름]") 환경.md 표의 값 하나

명령줄로도 쓴다(받아쓰기 모듈이 다른 파이썬에 깔려 있을 때 이 파일이 그 파이썬으로 자기 자신을 다시 부른다):
 python3 platform_util.py --transcribe <wav> [--language ko] [--no-words] [--condition]
 python3 platform_util.py --hdr-to-sdr <원본> <출력>
 python3 platform_util.py --info
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.expanduser("~/.cache/reels-edit")
MLX_MODEL = "mlx-community/whisper-large-v3-turbo"
FASTER_MODEL = "deepdml/faster-whisper-large-v3-turbo-ct2"


# ── 컴퓨터 ──────────────────────────────────────────────────────────────────
def os_kind():
    s = platform.system()
    if s == "Darwin":
        return "mac"
    if s == "Windows" or s.startswith(("MINGW", "MSYS", "CYGWIN")):
        return "win"
    return "other"


def is_apple_silicon():
    return os_kind() == "mac" and platform.machine() == "arm64"


def capcut_running():
    if os_kind() == "win":
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe"], capture_output=True, text=True)
        return "capcut.exe" in r.stdout.lower()
    return subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0


def capcut_drafts_dir():
    if os.environ.get("CAPCUT_DRAFT_DIR"):
        return os.environ["CAPCUT_DRAFT_DIR"]
    if os_kind() == "win":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return os.path.join(base, "CapCut", "User Data", "Projects", "com.lveditor.draft")
    return os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")


# ── 환경.md ─────────────────────────────────────────────────────────────────
def env_value(name):
    """환경.md 표에서 `| [이름] | 값 |` 의 값. 없으면 None. ~ 는 홈으로, [결과루트] 같은 참조는 한 번 풀어 준다."""
    p = os.path.join(SKILL, "환경.md")
    if not os.path.exists(p):
        return None
    vals = {}
    for line in open(p, encoding="utf-8"):
        m = re.match(r"\|\s*(\[[^\]]+\])\s*\|\s*(.*?)\s*\|\s*$", line)
        if m:
            vals[m.group(1)] = m.group(2)
    v = vals.get(name)
    if v is None:
        return None
    v = re.split(r"\s+\(", v)[0].strip("` ")  # 값 뒤 설명 괄호·코드 표시는 뺀다(템플릿 칸 "~/Projects/x (설명)")
    for k, x in vals.items():
        if k in v and k != name:
            v = v.replace(k, x)
    return os.path.expanduser(v) if v.startswith("~") else v


def remotion_dir():
    v = env_value("[Remotion폴더]")
    if v and os.path.isdir(v):
        return v
    return os.path.expanduser("~/Projects/reels-edit-remotion")


# ── 받아쓰기 ────────────────────────────────────────────────────────────────
def _shebang_python(tool):
    f = shutil.which(tool)
    if not f:
        return None
    try:
        first = open(f, "rb").readline().decode("utf-8", "ignore").strip()
    except OSError:
        return None
    if first.startswith("#!") and "python" in first:
        return first[2:].strip()
    return None


def whisper_engine():
    """이 컴퓨터에서 쓸 받아쓰기 엔진 이름과, 그 모듈이 들어 있는 파이썬 경로."""
    if is_apple_silicon():
        try:
            import mlx_whisper  # noqa: F401
            return "mlx", sys.executable
        except ImportError:
            py = _shebang_python("mlx_whisper")
            if py:
                return "mlx", py
    try:
        import faster_whisper  # noqa: F401
        return "faster", sys.executable
    except ImportError:
        py = _shebang_python("whisper-ctranslate2")
        if py:
            return "faster", py
    return "none", None


def _normalize(segments):
    out = []
    for s in segments:
        words = [{"word": w.get("word", ""), "start": float(w.get("start", 0)), "end": float(w.get("end", 0))}
                 for w in (s.get("words") or [])]
        out.append({"text": s.get("text", ""), "start": float(s.get("start", 0)), "end": float(s.get("end", 0)), "words": words})
    return {"text": " ".join(s["text"].strip() for s in out).strip(), "segments": out}


def _transcribe_here(wav, language, word_timestamps, condition):
    """지금 이 파이썬에 받아쓰기 모듈이 있을 때만."""
    if is_apple_silicon():
        try:
            import mlx_whisper
            r = mlx_whisper.transcribe(wav, path_or_hf_repo=MLX_MODEL, language=language,
                                       word_timestamps=word_timestamps, condition_on_previous_text=condition)
            return _normalize(r["segments"])
        except ImportError:
            pass
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    try:
        model = WhisperModel(FASTER_MODEL, device="cuda", compute_type="float16")
    except Exception:
        model = WhisperModel(FASTER_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(wav, language=language, word_timestamps=word_timestamps,
                               condition_on_previous_text=condition)
    out = []
    for s in segs:
        out.append({"text": s.text, "start": s.start, "end": s.end,
                    "words": [{"word": w.word, "start": w.start, "end": w.end} for w in (s.words or [])]})
    return _normalize(out)


def _transcribe_cli(wav, language, word_timestamps, condition):
    """whisper-ctranslate2 명령줄만 있을 때."""
    exe = shutil.which("whisper-ctranslate2")
    if not exe:
        return None
    tmp = tempfile.mkdtemp()
    cmd = [exe, wav, "--model", FASTER_MODEL, "--language", language, "--output_format", "json", "--output_dir", tmp,
           "--word_timestamps", "True" if word_timestamps else "False",
           "--condition_on_previous_text", "True" if condition else "False"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    jp = os.path.join(tmp, os.path.splitext(os.path.basename(wav))[0] + ".json")
    r = json.load(open(jp, encoding="utf-8"))
    shutil.rmtree(tmp, ignore_errors=True)
    return _normalize(r.get("segments", []))


def transcribe(wav, language="ko", word_timestamps=True, condition_on_previous_text=False):
    r = _transcribe_here(wav, language, word_timestamps, condition_on_previous_text)
    if r is not None:
        return r
    engine, py = whisper_engine()
    if py and os.path.abspath(py) != os.path.abspath(sys.executable):
 # 모듈이 다른 파이썬(uv tool 환경)에 있다 → 그 파이썬으로 이 파일을 다시 부른다
        cmd = [py, os.path.abspath(__file__), "--transcribe", wav, "--language", language]
        if not word_timestamps:
            cmd.append("--no-words")
        if condition_on_previous_text:
            cmd.append("--condition")
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
        sys.exit(f"받아쓰기 실패({engine}): {p.stderr[-400:]}")
    r = _transcribe_cli(wav, language, word_timestamps, condition_on_previous_text)
    if r is not None:
        return r
    sys.exit("받아쓰기 도구가 없어요. 맥(애플칩)은 `uv tool install mlx-whisper`, 그 외는 `uv tool install whisper-ctranslate2` 로 설치한 뒤 다시 해 주세요.")


# ── 영상 변환 ───────────────────────────────────────────────────────────────
def ffmpeg_has_filter(name):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return bool(re.search(rf"\s{name}\s", r.stdout))


def hdr_to_sdr(src, dst):
    """HDR(HLG·PQ) 영상을 SDR(bt709)로. 회전 정보도 화면에 반영된다."""
    if os_kind() == "mac" and shutil.which("avconvert"):
        subprocess.run(["avconvert", "-s", src, "-p", "PresetHighestQuality", "-o", dst, "--replace"],
                       check=True, stdout=subprocess.DEVNULL)
        return dst
    if not ffmpeg_has_filter("zscale"):
        sys.exit("이 ffmpeg 에는 HDR을 SDR로 바꾸는 zscale 필터가 없어요. 윈도우는 `winget install Gyan.FFmpeg`(full 판), 리눅스는 libzimg 가 든 ffmpeg 를 설치해 주세요.")
    vf = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
          "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, *video_encoder_args(),
                    "-c:a", "copy", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", dst], check=True)
    return dst


def video_encoder_args():
    """영상을 다시 압축해야 할 때의 인코더. 맥은 하드웨어(videotoolbox), 그 외는 libx264."""
    if os_kind() == "mac":
        return ["-c:v", "hevc_videotoolbox", "-b:v", "20M", "-tag:v", "hvc1"]
    return ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"]


# ── 얼굴·인물 ───────────────────────────────────────────────────────────────
def _swift_bin(name):
    """맥 전용: scripts/<name>.swift 를 ~/.cache/reels-edit/<name> 으로 컴파일해 둔다."""
    src = os.path.join(SKILL, "scripts", f"{name}.swift")
    out = os.path.join(CACHE, name)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(["swiftc", "-O", src, "-o", out], check=True)
    return out


def face_centers(jpg_paths):
    """사진마다 얼굴 가운데 [fx, fy] (0~1, 왼쪽 위 기준). 못 찾으면 None."""
    if not jpg_paths:
        return []
    if os_kind() == "mac":
        out = subprocess.run([_swift_bin("face_center"), *jpg_paths], capture_output=True, text=True).stdout.strip().splitlines()
        res = []
        for line in out:
            _, fx, fy = line.split("\t")
            fx, fy = float(fx), float(fy)
            res.append([round(fx, 3), round(fy, 3)] if fx >= 0 else None)
        return res + [None] * (len(jpg_paths) - len(res))
    try:
        import cv2
    except ImportError:
        print("⚠️ 얼굴 인식 도구(opencv)가 없어 화면 가운데를 기준으로 확대합니다. `pip install opencv-python` 으로 설치할 수 있어요.", file=sys.stderr)
        return [None] * len(jpg_paths)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    res = []
    for p in jpg_paths:
        img = cv2.imread(p)
        if img is None:
            res.append(None)
            continue
        h, w = img.shape[:2]
        faces = casc.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(max(20, w // 12),) * 2)
        if len(faces) == 0:
            res.append(None)
            continue
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        res.append([round((x + fw / 2) / w, 3), round((y + fh / 2) / h, 3)])
    return res


def person_matte(in_mp4, out_mov):
    """인물만 남긴 투명 영상(ProRes 4444). 성공하면 True, 도구가 없으면 False(오려내기 없이 쓰라는 뜻)."""
    tmp = tempfile.mkdtemp()
    try:
        if os_kind() == "mac":
            subprocess.run([_swift_bin("person_matte"), in_mp4, tmp], check=True, stdout=subprocess.DEVNULL)
        else:
            try:
                from rembg import remove
                from PIL import Image
            except ImportError:
                print("⚠️ 인물 오려내기 도구(rembg)가 없어 오려내지 않고 원래 화면 창으로 넣습니다. `pip install rembg pillow` 로 설치할 수 있어요.", file=sys.stderr)
                return False
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", in_mp4, "-vf", "fps=30", f"{tmp}/f_%05d.png"], check=True)
            for f in sorted(os.listdir(tmp)):
                if not f.startswith("f_"):
                    continue
                rgba = remove(Image.open(os.path.join(tmp, f)).convert("RGBA"))
                rgba.split()[-1].save(os.path.join(tmp, f.replace("f_", "m_")))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", in_mp4, "-framerate", "30", "-i", f"{tmp}/m_%05d.png",
                        "-filter_complex", "[1]format=gray,gblur=sigma=1.2[a];[0][a]alphamerge",
                        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", out_mov], check=True)
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 명령줄 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--transcribe":
        wav = a[1]
        lang = a[a.index("--language") + 1] if "--language" in a else "ko"
        r = _transcribe_here(wav, lang, "--no-words" not in a, "--condition" in a)
        if r is None:
            r = _transcribe_cli(wav, lang, "--no-words" not in a, "--condition" in a)
        if r is None:
            sys.exit("이 파이썬에는 받아쓰기 모듈이 없어요.")
        print(json.dumps(r, ensure_ascii=False))
    elif a and a[0] == "--hdr-to-sdr":
        hdr_to_sdr(a[1], a[2])
    elif a and a[0] == "--info":
        e, py = whisper_engine()
        print(json.dumps({"os": os_kind(), "apple_silicon": is_apple_silicon(), "whisper": e, "whisper_python": py,
                          "capcut_drafts": capcut_drafts_dir(), "remotion": remotion_dir()}, ensure_ascii=False))
    else:
        print(__doc__)


# ── 나레이션 (narration.py / narration_apply.py) ──
def load_narration(res):
    """<결과폴더>/narration.json 중 배치가 끝난 항목(at·wav·dur 있음)만. 없으면 빈 목록 — 나레이션이 없는 편집은 전과 똑같이 돈다."""
    p = os.path.join(res, "narration.json")
    if not os.path.exists(p):
        return []
    try:
        items = json.load(open(p, encoding="utf-8"))
    except Exception:
        return []
    return [it for it in items if it.get("at") is not None and it.get("wav") and os.path.exists(it["wav"]) and it.get("dur")]


def hold_video_filter(src_in, dur):
    """정지 화면 조각(hold)용 ffmpeg 필터 앞부분 — 원본 그 시각 한 프레임을 dur 초 동안 멈춰 보여 준다. 뒤에 scale 등을 이어 붙인다."""
    return (f"[0:v]trim=start={src_in}:end={src_in + 0.2},setpts=PTS-STARTPTS,fps=30,trim=end_frame=1,setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop_duration={dur + 0.1},trim=duration={dur},setpts=PTS-STARTPTS")


def narration_mix(inputs, fc, n_in, voice_label, res, out_label):
    """목소리 줄기([voice_label])에 나레이션 wav 들을 그 시각(at)에 섞어 [out_label]로. 나레이션이 없으면 이름만 바꿔 준다.
    inputs(ffmpeg -i 목록)·fc(필터 줄 목록)에 덧붙이고, 다음 입력 번호를 돌려준다."""
    items = load_narration(res)
    if not items:
        fc.append(f"[{voice_label}]acopy[{out_label}]")
        return n_in
    labels = [f"[{voice_label}]"]
    for k, it in enumerate(items):
        inputs += ["-i", it["wav"]]
        ms = int(round(it["at"] * 1000))
        fc.append(f"[{n_in}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[nar{k}]")
        labels.append(f"[nar{k}]")
        n_in += 1
    fc.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first[{out_label}]")
    return n_in
