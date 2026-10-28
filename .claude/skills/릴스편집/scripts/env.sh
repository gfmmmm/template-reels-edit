#!/usr/bin/env bash
# 공통 셸 조각 — 다른 .sh 스크립트가 `source "$(dirname "$0")/env.sh"` 로 불러 쓴다.
# 이 컴퓨터가 맥인지 윈도우인지 알아보고, 도구 이름·경로를 한 곳에서 정한다.
# (윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다. 윈도우는 클로드 코드가 쓰는 Git Bash 위에서 돈다고 가정한다.)
#
# 정하는 값
# OS mac | win | other
# ARCH arm64 | x86_64
# PY 실제로 도는 파이썬 명령 (python3 / python / py -3)
# WHISPER_ENGINE mlx(맥 애플칩) | faster(그 외, whisper-ctranslate2·faster_whisper) | none
# WHISPER_PY 받아쓰기 모듈이 들어 있는 파이썬 (uv tool 환경). 없으면 $PY
# CAPCUT_DRAFTS CapCut 프로젝트 폴더
# SKILL_DIR 이 스킬 폴더
# 함수
# capcut_running CapCut 앱이 켜져 있으면 0(참)

case "$(uname -s)" in
  Darwin) OS=mac ;;
  MINGW*|MSYS*|CYGWIN*) OS=win ;;
  *) OS=other ;;
esac
ARCH="$(uname -m)"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ "$OS" = win ]; then
 # winget 으로 깐 프로그램은 새 창을 열기 전까지 PATH 에 안 잡혀서, 설치 위치를 직접 붙인다
  LAD="$(cygpath -u "${LOCALAPPDATA:-$HOME/AppData/Local}" 2>/dev/null || echo "$HOME/AppData/Local")"
  for d in "$LAD/Microsoft/WinGet/Links" "$LAD"/Programs/Python/Python3*/ "$LAD"/Programs/Python/Python3*/Scripts "$HOME/AppData/Roaming/npm"; do
    [ -d "$d" ] && PATH="$d:$PATH"
  done
  export PATH
fi
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

# 파이썬: 윈도우의 "python3"은 설치가 안 됐으면 스토어 안내만 띄우는 가짜라, 실행해 보고 고른다
PY=""
for c in python3 python "py -3"; do
  if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then PY="$c"; break; fi
done

# 받아쓰기 엔진
WHISPER_ENGINE=none; WHISPER_PY="$PY"
_shebang_py() { # 도구 실행 파일의 첫 줄(#!경로)에서 파이썬 경로를 뽑는다
  local f; f="$(command -v "$1" 2>/dev/null)" || return 1
  local l; l="$(head -1 "$f" 2>/dev/null)"
  case "$l" in "#!"*python*) echo "${l#\#!}" ;; *) return 1 ;; esac
}
if [ "$OS" = mac ] && [ "$ARCH" = arm64 ] && command -v mlx_whisper >/dev/null 2>&1; then
  WHISPER_ENGINE=mlx; WHISPER_PY="$(_shebang_py mlx_whisper || echo "$PY")"
elif command -v whisper-ctranslate2 >/dev/null 2>&1; then
  WHISPER_ENGINE=faster; WHISPER_PY="$(_shebang_py whisper-ctranslate2 || echo "$PY")"
elif [ -n "$PY" ] && $PY -c "import faster_whisper" >/dev/null 2>&1; then
  WHISPER_ENGINE=faster
fi

# CapCut 프로젝트 폴더
if [ -n "${CAPCUT_DRAFT_DIR:-}" ]; then CAPCUT_DRAFTS="$CAPCUT_DRAFT_DIR"
elif [ "$OS" = win ]; then CAPCUT_DRAFTS="${LAD:-$HOME/AppData/Local}/CapCut/User Data/Projects/com.lveditor.draft"
else CAPCUT_DRAFTS="$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft"; fi

capcut_running() {
  if [ "$OS" = win ]; then
    tasklist /FI "IMAGENAME eq CapCut.exe" 2>/dev/null | grep -qi "CapCut.exe"
  else
    pgrep -x CapCut >/dev/null 2>&1
  fi
}

export OS ARCH PY WHISPER_ENGINE WHISPER_PY CAPCUT_DRAFTS SKILL_DIR
