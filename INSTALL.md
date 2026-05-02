# Astartes 설치 가이드

## 원라이너 설치 (권장)

터미널에서 한 줄 실행:

```bash
curl -fsSL https://raw.githubusercontent.com/SmallTyrant/Astartes/main/scripts/install.sh | bash
```

설치 완료 후 **Claude Code를 재시작**하면 바로 사용할 수 있습니다.

---

## 수동 설치

```bash
git clone --depth 1 https://github.com/SmallTyrant/Astartes.git /tmp/astartes

mkdir -p ~/.claude/agents ~/.claude/commands ~/.claude/skills ~/.claude/hooks

cp -r /tmp/astartes/.claude/agents/.  ~/.claude/agents/
cp -r /tmp/astartes/.claude/commands/. ~/.claude/commands/
cp -r /tmp/astartes/.claude/skills/.  ~/.claude/skills/
cp -r /tmp/astartes/.claude/hooks/.   ~/.claude/hooks/

pip install openpyxl
```

Claude Code 재시작 후 사용 가능합니다.

---

## XLSX 스킬만 설치 (경량)

TC 시트 export 기능만 필요한 경우:

```bash
curl -fsSL https://raw.githubusercontent.com/SmallTyrant/Astartes/main/scripts/install.sh | bash
```

동일 스크립트이며, 설치 후 `--export-only` 옵션으로 스킬만 사용할 수 있습니다.

---

## 설치 확인

Claude Code 채팅창에서:

```
/astartes-doctor --check
```

모든 항목이 ✓이면 준비 완료입니다.

---

## 업데이트

동일한 설치 스크립트를 다시 실행하면 최신 버전으로 업데이트됩니다:

```bash
curl -fsSL https://raw.githubusercontent.com/SmallTyrant/Astartes/main/scripts/install.sh | bash
```

---

## 제거

```bash
rm -rf ~/.claude/skills/astartes-tc
# 에이전트·명령어도 제거하려면:
# ~/.claude/agents/ 에서 Astartes 관련 파일 삭제
# ~/.claude/commands/ 에서 astartes-tc.md, astartes-doctor.md 삭제
```
