#!/usr/bin/env bash
# 4단계 음량 마무리: CapCut에서 내보낸 파일의 "소리만" 목표 음량 -12 LUFS(공용 규칙, — 계정이 바꾸려면 presets/음량.txt)·최고 -1.5 dBTP로 다듬는다. 화면은 다시 압축하지 않는다.
# 사용법: finish_audio.sh <내보낸 영상.mp4> [출력.mp4] (출력 기본: 같은 폴더 <이름>_업로드용.mp4)
# 왜: 효과음이 들리게 넣으면 목소리 최고점과 겹치는 순간 -1 dBTP를 넘기 쉽다. 효과음을 더 낮추면 안 들린다.
set -euo pipefail
IN="$1"; OUT="${2:-${IN%.*}_업로드용.mp4}"
LUFS=$(cat "$(dirname "$0")/../presets/음량.txt" 2>/dev/null || echo -12)
LIM="alimiter=limit=0.7:attack=3:release=40:level=0"
M=$(ffmpeg -nostats -i "$IN" -vn -af "$LIM,loudnorm=I=$LUFS:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
g(){ echo "$M" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
AF="$LIM,loudnorm=I=$LUFS:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000"
ffmpeg -v error -y -i "$IN" -map 0:v:0 -map 0:a:0 -c:v copy -af "$AF" -c:a aac -b:a 256k -movflags +faststart "$OUT"
python3 "$(dirname "$0")/ear_check.py" loudness "$OUT"
