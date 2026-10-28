#!/bin/bash
# ③-E 넘기기 전 최종 검수 한 번에 — 하나라도 실패하면 "완료"라고 하지 않는다.
# 사용법: final_check.sh <결과폴더> <CapCut 프로젝트> <CapCut에서 내보낸 영상> [승인본 영상(기본 <결과폴더>/preview/승인본_기준.mp4)]
# 순서: ① 프로젝트 글자 점검(글꼴·외곽선·줄 폭) ② 자막·이모지·라벨·메모 크기 전수 대조(승인본 기준)
# ③ 싱크·끝말 ④ 규격(1080×1920·30fps·SDR) ⑤ 소리 마무리 → <내보낸 영상>_업로드용.mp4
# ①~④가 모두 통과해야 ⑤를 한다. 결과는 <결과폴더>/최종검수.md 에 남긴다.
set -u
RES="$1"; PROJ="$2"; EXP="$3"; REF="${4:-$1/preview/승인본_기준.mp4}"
S="$(cd "$(dirname "$0")" && pwd)"
source "$(dirname "$0")/env.sh"; PY_W="${PY}"   # 받아쓰기 엔진은 platform_util 이 운영체제에 맞게 고른다(다른 파이썬에 있으면 거기서 다시 부른다)
OUT="$RES/최종검수.md"; fail=0
{
  echo "# 최종 검수 $(date '+%Y-%m-%d %H:%M')"; echo; echo "- 실물: $EXP"; echo "- 승인본: $REF"; echo
  echo "## ① 프로젝트 글자 점검"; python3 "$S/capcut_textfix.py" "$PROJ" --check 2>&1 | tail -3 || fail=1
  echo; echo "## ② 글자 크기 전수 대조"; python3 "$S/text_size_check.py" "$RES" "$EXP" "$REF" 2>&1 || fail=1
  echo; echo "## ③ 싱크·끝말"; "$PY_W" "$S/sync_check.py" "$RES" "$EXP" 2>&1 | grep -v Fetching || fail=1
  echo; echo "## ④ 규격"
  spec=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,color_transfer -of csv=p=0 "$EXP" | tr -d ' ')
  echo "$spec"
  case "$spec" in 1080,1920,*30/1*) ;; *) echo "규격 다름"; fail=1;; esac
  case "$spec" in *arib-std-b67*|*smpte2084*) echo "HDR — SDR로 내보내야 함"; fail=1;; esac
} > "$OUT" 2>&1
# 파이프 안의 fail은 서브셸이라 다시 판정
grep -qE "다름 [1-9]|실패|규격 다름|HDR —|문제 있음|Traceback" "$OUT" && fail=1
if [ "$fail" -eq 0 ]; then
  echo; echo "## ⑤ 소리 마무리" >> "$OUT"
  bash "$S/finish_audio.sh" "$EXP" >> "$OUT" 2>&1
  echo "통과 — 업로드용: ${EXP%.*}_업로드용.mp4" | tee -a "$OUT"
else
  echo "실패 — $OUT 를 보고 CapCut 프로젝트를 승인본에 맞춰 고친 뒤 다시 내보낸다(확인본을 실물에 맞추지 않는다)." | tee -a "$OUT"
  exit 1
fi
