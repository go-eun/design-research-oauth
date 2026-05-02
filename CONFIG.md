# 에이전트 설정 데이터

## ui_pattern 목록 (40개)

| # | 한국어 | 영문명 |
|---|---|---|
| 1 | AI | ai |
| 2 | 검색 | search |
| 3 | 게이미피케이션/퀴즈 | gamification / quiz |
| 4 | 카드/계좌 | card / account |
| 5 | 공지사항 | announcement |
| 6 | 글쓰기 | post |
| 7 | 내역/조회 | history / log |
| 8 | 내주변/지도 | nearby / map |
| 9 | 녹음하기 | recording |
| 10 | 로그인/회원가입 | login / sign-up |
| 11 | 리뷰 | review |
| 12 | 리뷰쓰기 | write-review |
| 13 | 리스트 | list |
| 14 | 마이페이지 | my-page |
| 15 | 메뉴/전체보기 | menu / all-view |
| 16 | 멤버십 | membership |
| 17 | 문의/고객센터/FAQ | help-center / faq |
| 18 | 북마크/위시리스트 | bookmark / wishlist |
| 19 | 사진촬영 | photo |
| 20 | 상세정보 | detail |
| 21 | 선물하기 | gift |
| 22 | 설정/제어 | settings / control |
| 23 | 스플래시 | splash |
| 24 | 신청/결정 | apply / confirmation |
| 25 | 알림/푸시 | notification / push |
| 26 | 예약/결제 | booking / checkout |
| 27 | 음성 | voice |
| 28 | 이벤트 | event |
| 29 | 장바구니 | cart |
| 30 | 채팅 | chat |
| 31 | 챗봇 | chatbot |
| 32 | 초대하기/받기 | invite / accept |
| 33 | 추천/메인 | feed / home |
| 34 | 취소/환불 | cancel / refund |
| 35 | 커뮤니티 | community |
| 36 | 포인트/쿠폰혜택 | points / coupon |
| 37 | 통계/리포트 | analytics / report |
| 38 | 튜토리얼/온보딩 | tutorial / onboarding |
| 39 | 필터 | filter |
| 40 | 에러/빈화면 | error / empty-state |

## category 목록 (14개)

| 영문명 | 한국어 예시 |
|---|---|
| health-fitness | 헬스, 운동, 피트니스, 건강 |
| finance | 금융, 은행, 주식, 핀테크 |
| commerce | 쇼핑, 커머스, 패션, 마켓 |
| lifestyle | 라이프스타일, 인테리어, 반려동물 |
| entertainment | OTT, 영화, 웹툰, 드라마 |
| social | SNS, 커뮤니티, 메신저 |
| productivity | 업무, 메모, 캘린더, 협업 |
| education | 교육, 학습, 영어, 자격증 |
| utility | 유틸리티, 날씨, 계산기, 번역 |
| sports | 야구, 골프, 축구, 스포츠 |
| music | 음악, 노래, 악기, 팟캐스트 |
| navigation | 지도, 내비, 대중교통, 길찾기 |
| photo-video | 사진, 카메라, 영상편집 |
| business | 비즈니스, 취업, 채용, 재택 |

## 되묻기 문구용 한국어 변환 규칙

ui_pattern → 되묻기 문구 생성 규칙:
`{ui_pattern} 화면을 다른 앱 이름으로 검색`

예시:
- 로그인/회원가입 → "로그인/회원가입 화면을 다른 앱 이름으로 검색"
- 추천/메인 → "추천/메인 화면을 다른 앱 이름으로 검색"
- 마이페이지 → "마이페이지 화면을 다른 앱 이름으로 검색"
- 튜토리얼/온보딩 → "튜토리얼/온보딩 화면을 다른 앱 이름으로 검색"

## 유의어 목록 참조

ui_pattern 유의어는 search_drive.py의 `UI_PATTERN_SYNONYMS`에서 관리.
CONFIG.md에 중복 정의하지 않음 (Single Source of Truth 원칙).

수정이 필요한 경우:
~/workspace/design-research/screenshot-helper/search_drive.py
→ UI_PATTERN_SYNONYMS 딕셔너리 직접 수정