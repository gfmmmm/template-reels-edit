#!/usr/bin/env bash
# 2단계 ⓪ 전처리: 원본은 건드리지 않고 [결과폴더]/media/에 편집용 복사본을 만든다.
# 사용법: preprocess.sh <원본 영상> <출력 파일.mov> [--voice] [--deshake] [--grade "<ffmpeg 색 필터>"]
# 선택(정답지 대조 — 편집자가 한 대사 정리·흔들림 보정·색 보정. 메뉴얼 1·10번이 켤지 정한다):
# --voice 대사 정리: 저음 웅웅 소리 컷(80Hz) → 바탕 잡음 줄이기(afftdn, 잰 바탕 잡음 기준) → -14 LUFS.
# 문장마다 크기 고르게 하기는 컷 설계 뒤 voice_level.py 가 한다(질문자·설명하는 사람 크기 차이 — 프레임 단위 자동 크기 맞춤
# speechnorm·dynaudnorm 은 차이를 거의 못 줄이거나 말 없는 구간 잡음을 -50→-34dB 로 키워서 쓰지 않는다 실측)
# --deshake 손떨림 보정(stabilize.py 이동 보정 — ffmpeg deshake 는 아이폰 손떨림을 못 줄여서 안 쓴다). 흔들림이 큰지는
# shake_check.py 로 먼저 잰다("큼"만). 보정해도 안 줄면 stabilize.py 가 원본을 그대로 둔다
# --grade 색 보정 필터(예: "eq=contrast=1.04:saturation=1.08:brightness=0.01", "lut3d=file=계정.cube") — 계정 값은 presets/색보정.txt
# --deshake·--grade 를 쓰면 영상을 다시 만든다(그 밖엔 영상은 그대로 복사)
# - HDR(HLG/PQ)이면 SDR로 변환 + 회전 반영. 맥은 avconvert(PresetHighestQuality), 그 외는 ffmpeg zscale (platform_util.hdr_to_sdr).
# (맥 ffmpeg에는 zscale이 없고 scale_vt는 색 변환을 못 해서 avconvert를 쓴다. ProRes 프리셋은 HDR이 그대로 남는다)
# - 소리는 좌우 같은 크기로(두 채널 섞기). 영상은 다시 압축하지 않고(copy) 소리만 -14 LUFS(최고 -2 dBTP — 효과음이 얹힐 여유), 2채널, 48kHz로 맞춘다.
# - 30fps가 아니거나 SDR인데 크기가 다르면 그때만 영상을 다시 만든다(맥 videotoolbox / 그 외 libx264).
# 윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
set -euo pipefail
SRC="$1"; OUT="$2"; shift 2
VOICE=0; DESHAKE=0; GRADE=""
while [ $# -gt 0 ]; do case "$1" in --voice) VOICE=1; shift ;; --deshake) DESHAKE=1; shift ;; --grade) GRADE="$2"; shift 2 ;; *) shift ;; esac; done
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/env.sh"
[ -n "$PY" ] || { echo "❌ 파이썬이 없어요 — 0단계 설치를 먼저 해 주세요"; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

TRC=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "$SRC" | tr -d ",[:space:]")
if [[ "$TRC" == "arib-std-b67" || "$TRC" == "smpte2084" ]]; then
  if [ "$OS" = mac ]; then echo "HDR($TRC) → SDR 변환 중 (avconvert)"; else echo "HDR($TRC) → SDR 변환 중 (ffmpeg zscale)"; fi
  $PY "$D/platform_util.py" --hdr-to-sdr "$SRC" "$TMP/sdr.mov"
  V="$TMP/sdr.mov"
else
  V="$SRC"
fi

FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$V" | tr -d ",[:space:]")
VF="fps=30"
if [ "$DESHAKE" = 1 ]; then $PY "$D/stabilize.py" "$V" "$TMP/stab.mov"; V="$TMP/stab.mov"; fi
[ -n "$GRADE" ] && VF="$VF,$GRADE"
if [[ "$FPS" == "30/1" && -z "$GRADE" ]]; then VOPT=(-c:v copy)
elif [ "$OS" = mac ]; then VOPT=(-vf "$VF" -c:v hevc_videotoolbox -b:v 20M -tag:v hvc1)
else VOPT=(-vf "$VF" -c:v libx264 -crf 16 -preset medium -pix_fmt yuv420p); fi

# 소리 2패스: 먼저 재고, 잰 값으로 정확히 맞춘다
# 튀는 순간만 리미터로 눌러(-8dBFS) 여유를 만든 뒤 -14 LUFS로 올린다. 최고점을 -3 dBTP로 묶으면 평균이 -15.8에서 못 올라와 -2로 둔다.
# 아이폰 스테레오는 두 마이크 크기가 달라(한쪽이 6dB 큰 경우가 있다) 한쪽만 크게 들린다 → 두 채널을 섞어 좌우 똑같이
MONO="pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"
LIM="$MONO,alimiter=limit=0.4:attack=5:release=50:level=0"
if [ "$VOICE" = 1 ]; then
 # 바탕 잡음 높이를 재서 afftdn 에 준다 — 너무 세게 지우면 말소리가 물속처럼 된다
 # 0.1초 창마다 크기를 재고, 디지털 무음(-80dB 아래 — 아이폰 원본 앞뒤)을 뺀 뒤 조용한 10%의 중앙값.
 # 아이폰 원본은 기기가 이미 잡음을 줄여 조용한 곳이 -70dB 안팎이다 — 그때 afftdn 은 거의 안 걸리고 저음 컷이 주 효과
  NF=$(ffmpeg -nostats -i "$V" -vn -af "$MONO,aresample=48000,asetnsamples=4800,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" -f null - 2>&1 | $PY -c "
import re,sys
v=sorted(float(x) for x in re.findall(r'RMS_level=(-?[0-9.]+)', sys.stdin.read()) if float(x)>-80)
q=v[:max(1,len(v)//10)]
print(max(-70, min(-30, round(q[len(q)//2]))) if v else -50)")
  LIM="$MONO,highpass=f=80,afftdn=nr=12:nf=$NF:tn=1,alimiter=limit=0.4:attack=5:release=50:level=0"
  echo "대사 정리: 저음 컷 + 바탕 잡음 ${NF}dB 기준으로 줄이기"
fi
M=$(ffmpeg -nostats -i "$V" -vn -af "$LIM,loudnorm=I=-14:TP=-2:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
g(){ echo "$M" | $PY -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
if [[ "$(g input_i)" == *inf* ]]; then AF="$LIM,aresample=48000"; echo "소리가 거의 없는 영상 — 크기 맞추기는 건너뜀"; else
AF="$LIM,loudnorm=I=-14:TP=-2:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000"
fi

ffmpeg -v error -y -i "$V" -map 0:v:0 -map 0:a:0 "${VOPT[@]}" -af "$AF" -ac 2 -c:a pcm_s16le \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 "$OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,color_transfer,channels -of compact "$OUT"
