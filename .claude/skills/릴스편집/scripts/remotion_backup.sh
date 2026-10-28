#!/usr/bin/env bash
# Remotion 작업 폴더([Remotion폴더], 맥에만 있음)의 소스를 스킬 안 remotion/ 로 복사해 드라이브에 남긴다.
# 사용: bash scripts/remotion_backup.sh — brand.ts·장면 컴포넌트를 고쳤을 때마다 한 번
# 제외: node_modules(npm install 로 다시 생김), out(렌더 결과), public/videos(편집마다 다른 영상 1GB 넘음)
# 복원: 새 컴퓨터에서 0단계 setup.sh 가 스킬 안 remotion/ 을 [Remotion폴더]로 복사하고 npm install 한다.
D="$(cd "$(dirname "$0")" && pwd)"; source "$D/env.sh"
REM="$($PY - "$SKILL_DIR" <<'PYEOF'
import re, sys, os
v = ""
for l in open(os.path.join(sys.argv[1], "환경.md"), encoding="utf-8"):
    m = re.match(r"\|\s*\[Remotion폴더\]\s*\|\s*(.*?)\s*\|", l)
    if m: v = m.group(1).split(" (")[0].strip()  # 값 뒤 괄호 설명은 뗀다
print(os.path.expanduser(v or "~/Projects/reels-edit-remotion"))
PYEOF
)"
[ -f "$REM/package.json" ] || { echo "❌ Remotion 폴더가 없어요: $REM"; exit 1; }
mkdir -p "$SKILL_DIR/remotion"
rsync -a --delete --exclude node_modules --exclude out --exclude 'public/videos' --exclude '.DS_Store' "$REM/" "$SKILL_DIR/remotion/"
echo "복사함: $REM → $SKILL_DIR/remotion ($(du -sh "$SKILL_DIR/remotion" | cut -f1)) · $(date +%Y-%m-%d)"
