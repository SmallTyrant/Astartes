# TC 스키마 v3 (시트 형식 통일)

기준 스프레드시트 컬럼과 1:1 정합:

```
TC ID | priority | 1 Step | 2 Step | 3 Step | 4 Step | 5 Step | pre-condition | 기대결과 | result | Jira ticket
```

---

## JSON 필수 필드 (시트 컬럼과 동일 의미)

| 필드          | 타입       | 시트 컬럼          | 비고                                                                   |
| ------------- | ---------- | ------------------ | ---------------------------------------------------------------------- |
| `tc_id`       | int        | `TC ID`            | 탭 내부에서 1부터 연속                                                 |
| `screen`      | string     | (탭 분리 키)       | 화면 이름 (예: `"메인 페이지"`)                                        |
| `platform`    | enum       | (탭 분리 키)       | `and` \| `ios` \| `web` (Android는 `and`)                              |
| `priority`    | enum       | `priority`         | `high` \| `mid` \| `low`                                               |
| `precondition` | string    | `pre-condition`    | 단일 문자열, 비어있으면 `""`                                           |
| `steps`       | string[]   | `1 Step`~`5 Step`  | 길이 1~5, 각 원소가 시트 컬럼에 차례로 들어감                          |
| `expected`    | string     | `기대결과`         | 단일 문자열, step별 기대결과는 마지막에 누적 서술                      |
| `jira_ticket` | string     | `Jira ticket`      | 기본 `""`                                                              |
| `result`      | string     | `result`           | **항상 `""`로 초기화** (실행 후 QA가 채움). 자동으로 채우지 말 것       |

---

## JSON 내부 전용 필드 (시트 export 시 제외)

| 필드             | 타입      | 용도                                                              |
| ---------------- | --------- | ----------------------------------------------------------------- |
| `requirement_id` | string    | 추적성 매핑                                                       |
| `source_refs[]`  | object[]  | `[{type: figma\|notion\|slack\|pdf\|prd\|api, id, url?, locator?}]` 입력 소스 역추적 |
| `risk_tags[]`    | string[]  | `auth`, `session`, `data`, `input`, `network`, `storage`, `payment`, `perf`, `a11y`, `i18n` 등 |
| `negative`       | bool      | `true` 면 부정/예외 TC                                            |
| `needs_review`   | bool      | `true` 면 사람 리뷰 필요 (자동 생성 신뢰도가 낮은 케이스)          |

이 필드들은 JSON에 보존되지만 시트 export 시 컬럼으로 출력되지 않는다.
`outputs/traceability.csv` 와 coverage 분석에서만 참조.

---

## 예시 JSON (단건)

```json
{
  "tc_id": 1,
  "screen": "구독 및 결제",
  "platform": "ios",
  "priority": "high",
  "precondition": "App Store 로그인 완료, 무료 플랜 사용 중",
  "steps": [
    "설정 → 구독 화면에 진입한다",
    "'프로' 플랜 카드를 탭한다",
    "결제 시트에서 '구매' 버튼을 탭한다",
    "Face ID 인증을 완료한다"
  ],
  "expected": "프로 플랜으로 업그레이드되고 영수증 화면이 표시되어야 한다",
  "jira_ticket": "",
  "result": "",
  "requirement_id": "REQ-PAY-001",
  "source_refs": [
    {"type": "prd", "id": "구독_및_결제.md#L12-L34"}
  ],
  "risk_tags": ["payment", "auth"]
}
```

---

## 탭 분리 규칙

- 한 화면을 여러 플랫폼에서 검증하면 `(screen, platform)` 조합마다 별도 JSON/CSV 파일 1개.
- 동일 시나리오가 플랫폼 간 공통이면 각 플랫폼 파일에 동일한 step으로 복제 (시트 구조와 동일).
- platform별 차이 (예: 생체인증 정책)는 해당 플랫폼 파일의 `steps`에서만 반영.

파일명 규칙: `outputs/testcases/{screen-slug}_{and|ios|web}.json`
시트 탭 이름: `{screen}_{platform}` (Excel 31자 제한, 슬라이스됨)

---

## 호환성 (구 스키마 → v3)

구 필드만 있는 JSON은 normalizer가 v3로 마이그레이션 후 검증 통과:

| 구 필드             | v3 매핑                      |
| ------------------- | ---------------------------- |
| `id`                | `tc_id`                      |
| `title`             | `expected` 일부 또는 step 1   |
| `category`          | `risk_tags[]` 후보            |
| `platforms[]`       | 플랫폼별 파일로 복제         |
| `preconditions[]`   | `precondition` (join "; ")    |
| `steps[].action`    | `steps[]` 각 원소             |
| `steps[].expected`  | `expected` 누적 서술          |

마이그레이션 후 PostToolUse 훅이 v3 스키마 검증을 자동 수행.

---

## 검증 항목 (JSON 정합성)

- `tc_id` 가 탭 내부에서 1부터 연속 (gap 없음).
- `platform` 이 `and|ios|web` 중 하나.
- `priority` 가 `high|mid|low` 중 하나.
- `steps` 배열 길이가 1~5.
- 각 `steps[i]` 가 단일 동작 (자세한 건 `step-decomposition.md`).
- `result` 가 `""`.
- 고위험 risk_tag (`auth|data|payment|network|storage`) 영역의 TC는 `priority="high"`.

위반 시 JSON을 고치고 export 재실행. 시트만 수정하면 다음 export에서 덮어써진다.
