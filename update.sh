#!/usr/bin/env bash
# 새 버전 받기 — 도구 부분만 새 판으로 바꾸고, 내가 키운 것은 남긴다.
# 사용: bash update.sh            (이 폴더 맨 위에서)
# 남기는 것: 편집메뉴얼.md · 환경.md · presets/ · 계정자료/ · 효과음 등록분(sfx/files·templates·palette_*.json·sfx-catalog.md)
#           · Remotion 폴더의 brand.ts·plan 파일(Remotion 폴더 쪽은 부품 소스만 새로 바꾼다)
# 옛 판은 _보관/옛_릴스편집_<날짜시각>/ 에 통째로 남긴다.
# 이 파일 자신도 새 판으로 바뀌므로, 끝까지 읽은 뒤 실행되게 전부 main 안에 둔다.

main() {
  set -e
  ROOT="$(cd "$(dirname "$0")" && pwd)"
  REPO="gfmmmm/template-reels-edit"; BRANCH="main"
  SK="$ROOT/.claude/skills/릴스편집"
  [ -d "$SK" ] || { echo "❌ 이 폴더에 릴스편집 도구가 없어요: $SK"; exit 1; }
  OLDV="$(cat "$ROOT/VERSION" 2>/dev/null || echo '?')"
  STAMP="$(date +%Y%m%d_%H%M%S)"
  KEEP="$ROOT/_보관/옛_릴스편집_$STAMP"

  if [ -d "$ROOT/.git" ]; then
    # git 으로 받은 폴더 — 내가 키운 것은 .gitignore 에 있어 pull 이 건드리지 않는다
    mkdir -p "$KEEP" && cp -R "$SK" "$KEEP/릴스편집"
    if ! git -C "$ROOT" pull --ff-only; then
      echo "❌ 새 판을 받지 못했어요. 도구 파일을 직접 고친 곳이 있으면 이렇게 돼요 — Claude 에게 'git 상태 보고 해결해줘'라고 말해 주세요."
      exit 1
    fi
  else
    TMP="$(mktemp -d)"
    echo "새 판 내려받는 중…"
    # tar.gz 로 받는다 — 맥 기본 unzip 은 깃허브 zip 의 한글 파일 이름(릴스편집·릴스검수)을 깨뜨린다
    curl -fsSL -o "$TMP/new.tar.gz" "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" || { echo "❌ 내려받기 실패 — 인터넷 연결을 확인해 주세요"; exit 1; }
    tar -xzf "$TMP/new.tar.gz" -C "$TMP" && rm -f "$TMP/new.tar.gz"
    NEW="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
    [ -f "$NEW/.claude/skills/릴스편집/SKILL.md" ] || { echo "❌ 받은 파일이 이상해요(도구 본체가 없음)"; exit 1; }
    NEWV="$(cat "$NEW/VERSION" 2>/dev/null || echo '?')"
    if [ "$OLDV" = "$NEWV" ]; then echo "이미 최신판이에요 ($OLDV)"; rm -rf "$TMP"; exit 0; fi

    # ① 옛 판 보관
    mkdir -p "$KEEP"
    cp -R "$SK" "$KEEP/릴스편집"
    [ -d "$ROOT/.claude/agents" ] && cp -R "$ROOT/.claude/agents" "$KEEP/agents"

    # ② 도구 부분 바꾸기
    rm -rf "$SK"
    cp -R "$NEW/.claude/skills/릴스편집" "$SK"
    mkdir -p "$ROOT/.claude/agents" && cp "$NEW/.claude/agents/"*.md "$ROOT/.claude/agents/"
    cp "$NEW/.claude/CLAUDE.md" "$ROOT/.claude/CLAUDE.md"
    cp "$NEW/.claude/settings.json" "$ROOT/.claude/settings.json"
    for f in README.md SETUP.md VERSION .gitignore; do [ -f "$NEW/$f" ] && cp "$NEW/$f" "$ROOT/$f"; done

    # ③ 내가 키운 것 되돌리기
    O="$KEEP/릴스편집"
    for f in 환경.md 편집메뉴얼.md; do [ -f "$O/$f" ] && cp "$O/$f" "$SK/$f"; done
    for d in presets 계정자료; do [ -d "$O/$d" ] && { rm -rf "$SK/$d"; cp -R "$O/$d" "$SK/$d"; }; done
    mkdir -p "$SK/sfx"
    for d in files templates; do [ -d "$O/sfx/$d" ] && { rm -rf "$SK/sfx/$d"; cp -R "$O/sfx/$d" "$SK/sfx/$d"; }; done
    for f in "$O"/sfx/palette_*.json "$O/sfx/sfx-catalog.md"; do [ -f "$f" ] && cp "$f" "$SK/sfx/"; done
    [ -f "$O/remotion/src/brand.ts" ] && cp "$O/remotion/src/brand.ts" "$SK/remotion/src/brand.ts"

    # update.sh 자신은 맨 마지막에 바꾼다
    cp "$NEW/update.sh" "$ROOT/update.sh.new"
    rm -rf "$TMP"
  fi

  # ④ Remotion 폴더(이 폴더 밖)에 새 부품 소스 반영 — brand.ts·plan 파일·영상은 그대로. 여기부터는 실패해도 멈추지 않는다
  set +e
  source "$SK/scripts/env.sh"
  REM="$($PY - "$SK" <<'PYEOF' 2>/dev/null
import re, sys, os
v = ""
p = os.path.join(sys.argv[1], "환경.md")
if os.path.exists(p):
    for l in open(p, encoding="utf-8"):
        m = re.match(r"\|\s*\[Remotion폴더\]\s*\|\s*(.*?)\s*\|", l)
        if m: v = re.split(r"\s+\(", m.group(1))[0].strip("\x60 ")
print(os.path.expanduser(v or "~/Projects/reels-edit-remotion"))
PYEOF
)"
  if [ -n "$REM" ] && [ -f "$REM/package.json" ]; then
    $PY - "$SK/remotion" "$REM" <<'PYEOF'
import os, shutil, sys, filecmp
src, dst = sys.argv[1], sys.argv[2]
n = 0
for root, _, fs in os.walk(os.path.join(src, "src")):
    for f in fs:
        if f == "brand.ts" or (f.startswith("plan") and f.endswith(".json")) or f == ".DS_Store": continue
        sp = os.path.join(root, f); dp = os.path.join(dst, os.path.relpath(sp, src))
        if os.path.exists(dp) and filecmp.cmp(sp, dp, shallow=False): continue
        os.makedirs(os.path.dirname(dp), exist_ok=True); shutil.copy2(sp, dp); n += 1
print(f"Remotion 부품 {n}개 새로 반영")
PYEOF
    if ! cmp -s "$SK/remotion/package.json" "$REM/package.json"; then
      cp "$SK/remotion/package.json" "$REM/package.json"
      [ -f "$SK/remotion/package-lock.json" ] && cp "$SK/remotion/package-lock.json" "$REM/package-lock.json"
      (cd "$REM" && npm install >/dev/null 2>&1) && echo "Remotion 패키지 새로 설치" || echo "⚠️ Remotion 패키지 설치가 안 됐어요 — Claude 에게 '$REM 에서 npm install 해줘'라고 말해 주세요"
    fi
  fi

  rm -f "$HOME/.cache/릴스편집/doctor_ok"   # 다음 편집 때 한 번 전체 점검
  echo "✅ 업데이트 끝: $OLDV → $(cat "$ROOT/VERSION" 2>/dev/null)"
  echo "   내가 키운 것(편집메뉴얼·환경·프리셋·효과음·글꼴·brand.ts)은 그대로예요. 옛 판: _보관/옛_릴스편집_$STAMP"
  if [ -f "$ROOT/update.sh.new" ]; then mv -f "$ROOT/update.sh.new" "$ROOT/update.sh"; fi
  exit 0
}
main "$@"; exit $?
