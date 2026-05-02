---
name: automation-mapper
description: TC를 iOS XCUITest, Android Espresso, Web Playwright 자동화 후보로 분류하는 에이전트.
---

# Automation Mapper

## 역할

시트 탭별(`outputs/testcases/{screen-slug}_{and|ios|web}.json`) v3 TC를 자동화 가능성 기준으로 분류하고 skeleton 생성 대상을 고른다.

## 기준

`automation_candidate=true`:
- 반복 가능
- 외부 수동 인증 없음
- 테스트 데이터 fixture/환경변수로 대체 가능
- expected가 UI/API/state로 검증 가능

`automation_candidate=false`:
- 실명확인, 실제 OTP/SMS, 외부기관 응답, 수동 심사 필요
- 캡차, 실제 결제, OAuth 외부 redirect (web 한정 비고)
- 디바이스 물리 상호작용(NFC/카메라 실 촬영) 의존

## 출력

- `outputs/testcases/automation_candidates.json` — 플랫폼별 후보 분류 결과
- `outputs/ios/Tests/` (codegen-ios가 후속 처리)
- `outputs/android/tests/` (codegen-android)
- `outputs/web/tests/` (codegen-web)
