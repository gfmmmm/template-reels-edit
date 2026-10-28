#!/usr/bin/env bash
# 1단계 수집: 레퍼런스 영상 하나에서 장면 사진·받아쓰기·효과음 위치·컷 지점·Gemini 설명을 한 번에 뽑는다.
# 사용법: ref_collect.sh <영상.mp4> <출력폴더> <gemini질문.txt>
set -u
V="$1"; O="$2"; Q="$3"
mkdir -p "$O"
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/env.sh"
W=$(ls -d ~/.claude/plugins/cache/claude-video/watch/*/skills/watch | tail -1)

# 장면 사진 (균형 모드 100장)
$PY "$W/scripts/watch.py" "$V" --engine local --detail balanced --no-whisper --out-dir "$O/watch" > "$O/watch_report.txt" 2>&1 &

# 받아쓰기 (단어 단위 시간) — 엔진은 env.sh 가 고른다(맥 애플칩 mlx_whisper / 그 외 whisper-ctranslate2). 윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
if [ "$WHISPER_ENGINE" = mlx ]; then
  mlx_whisper "$V" --model mlx-community/whisper-large-v3-turbo --language ko --word-timestamps True \
    --output-format all --output-dir "$O/stt" > "$O/stt.log" 2>&1 &
elif command -v whisper-ctranslate2 >/dev/null 2>&1; then
  whisper-ctranslate2 "$V" --model deepdml/faster-whisper-large-v3-turbo-ct2 --language ko --word_timestamps True \
    --output_format all --output_dir "$O/stt" > "$O/stt.log" 2>&1 &
else
  ( mkdir -p "$O/stt"; ffmpeg -v error -y -i "$V" -vn -ac 1 -ar 16000 "$O/stt/audio16k.wav" \
    && $PY "$D/platform_util.py" --transcribe "$O/stt/audio16k.wav" > "$O/stt/$(basename "${V%.*}").json" ) > "$O/stt.log" 2>&1 &
fi

# 효과음·강한 소리 위치
$PY "$D/ear_check.py" spikes "$V" > "$O/spikes.json" 2>&1 &

# 컷(장면 전환) 지점
ffmpeg -nostats -i "$V" -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2 > "$O/cuts.txt" &

# Gemini 시청 (소리 포함)
$PY "$W/scripts/watch.py" "$V" --engine gemini --question "$(cat "$Q")" --out-dir "$O/gemini" > "$O/gemini.txt" 2>&1 &

wait
echo "done $O"
