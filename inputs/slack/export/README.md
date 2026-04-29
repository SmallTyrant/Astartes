# inputs/slack/export

토큰 없이 Slack 스레드를 직접 드롭하는 경로.

## 사용법

스레드 텍스트/JSON을 export 후 이 폴더에 그대로 떨어뜨린다.

```
inputs/slack/export/<thread-name>.json
inputs/slack/export/<thread-name>.txt
```

`/gen-tc local` 또는 `/gen-tc local,figma:URL ios,web` 호출 시 `mcp-ingester`가 자동으로 스캔해 `inputs/slack/raw/`로 정규화 복사한다.

## 포맷 권장

- JSON: `[{"ts": "...", "user": "...", "text": "...", "thread_ts": "..."}, ...]`
- 텍스트: 한 줄당 한 메시지. ts/user/text가 식별 가능하면 됨.

## 금지 사항

- PII/시크릿(주민번호·계좌번호·OTP·토큰·API 키) 평문 포함 금지. fixture / env 경유.

상세 가이드: ../../README.md
