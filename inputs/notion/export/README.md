# inputs/notion/export

토큰 없이 Notion 페이지를 직접 드롭하는 경로.

## 사용법

Notion 페이지를 Markdown 또는 JSON으로 export 후 이 폴더에 떨어뜨린다.

```
inputs/notion/export/<page-name>.md
inputs/notion/export/<page-name>.json
```

`/gen-tc local` 또는 `/gen-tc local,figma:URL ios,web` 호출 시 `mcp-ingester`가 자동으로 스캔해 `inputs/notion/raw/`로 정규화 복사한다.

## 포맷 권장

- Markdown: 페이지를 그대로 export.
- JSON: Notion API `pages.retrieve` / `blocks.children.list` 응답 그대로.
- 폴더 단위 export도 지원 (서브 페이지 포함).

## 금지 사항

- PII/시크릿(주민번호·계좌번호·OTP·토큰·API 키) 평문 포함 금지. fixture / env 경유.

상세 가이드: ../../README.md
