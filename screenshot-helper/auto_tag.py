import os
import json
import base64
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# ── 환경변수 로드 ───────────────────────────────────────────
load_dotenv(os.path.expanduser("~/workspace/.env"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

BASE_DIR   = os.path.expanduser("~/workspace/design-research/screenshot-helper/captures")
TOKEN_PATH = os.path.expanduser("~/workspace/design-research/screenshot-helper/token.json")
FAILED_LOG = os.path.expanduser("~/workspace/design-research/screenshot-helper/upload_failed.log")
DRIVE_ROOT = '17b9qKIbvJvDzqgp_Ww696t2rIjg-0X1Y'
SCOPES     = ['https://www.googleapis.com/auth/drive']

UI_PATTERNS = [
    "AI", "검색", "게이미피케이션/퀴즈", "카드/계좌", "공지사항", "글쓰기",
    "내역/조회", "내주변/지도", "녹음하기", "로그인/회원가입", "리뷰", "리뷰쓰기",
    "리스트", "마이페이지", "메뉴/전체보기", "멤버십", "문의/고객센터/FAQ",
    "북마크/위시리스트", "사진촬영", "상세정보", "선물하기", "설정/제어",
    "스플래시", "신청/결정", "알림/푸시", "예약/결제", "음성", "이벤트",
    "장바구니", "채팅", "챗봇", "초대하기/받기", "추천/메인", "취소/환불",
    "커뮤니티", "포인트/쿠폰혜택", "통계/리포트", "튜토리얼/온보딩", "필터", "에러/빈화면",
]

_folder_cache = {}

# ── Drive 연결 ─────────────────────────────────────────────
def get_drive_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        else:
            raise Exception("token.json이 만료됐어요. auth_test.py를 다시 실행해주세요.")
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, name, parent_id):
    cache_key = f"{parent_id}/{name}"
    if cache_key in _folder_cache:
        return _folder_cache[cache_key]
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(
        q=query, fields='files(id)',
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    files = results.get('files', [])
    if files:
        folder_id = files[0]['id']
    else:
        meta = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(
            body=meta, fields='id', supportsAllDrives=True
        ).execute()
        folder_id = folder['id']
    _folder_cache[cache_key] = folder_id
    return folder_id

def update_drive_json(service, local_path, category, app_name, date_str):
    for attempt in range(3):
        try:
            folder_id = DRIVE_ROOT
            for part in [category.strip(), app_name.strip(), date_str.strip()]:
                folder_id = get_or_create_folder(service, part, folder_id)

            file_name = os.path.basename(local_path)
            query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query, fields='files(id)',
                supportsAllDrives=True, includeItemsFromAllDrives=True
            ).execute()
            files = results.get('files', [])
            media = MediaFileUpload(local_path, mimetype='application/json')

            if files:
                service.files().update(
                    fileId=files[0]['id'],
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
            else:
                service.files().create(
                    body={'name': file_name, 'parents': [folder_id]},
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
            print(f"  ☁️  Drive JSON 업데이트 완료!")
            return True
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️  Drive 업데이트 3회 실패: {e}")
                with open(FAILED_LOG, "a", encoding="utf-8") as log:
                    log.write(f"{local_path}\n")
                return False

def cleanup_empty_dirs(path):
    folder = os.path.dirname(path)
    while folder != BASE_DIR:
        try:
            if not os.listdir(folder):
                os.rmdir(folder)
                folder = os.path.dirname(folder)
            else:
                break
        except Exception:
            break

def parse_tokens(raw):
    raw = raw.replace(',', ' ')
    return [t.strip() for t in raw.split() if t.strip()]

# ── Claude Vision 자동 태깅 ────────────────────────────────
def analyze_image(png_path, app_name):
    """Claude Vision으로 이미지 분석 → ui_pattern / notes 추천"""
    if not ANTHROPIC_API_KEY:
        raise Exception("ANTHROPIC_API_KEY가 .env에 없어요.")

    with open(png_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = f"""이 이미지는 '{app_name}' 앱의 UI 스크린샷이야.
아래 기준으로 분석해서 JSON만 반환해줘. 다른 텍스트 없이 JSON만.

ui_pattern 후보 (복수 선택 가능):
{', '.join(UI_PATTERNS)}

{{
  "ui_pattern": ["해당하는 패턴들"],
  "notes": "화면 특징 한 줄 요약",
  "reason": "판단 근거 한 줄"
}}"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        },
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ── 미태깅 파일 탐색 ───────────────────────────────────────
def find_untagged():
    all_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for f in sorted(files):
            if f.endswith(".json") and f != "hash_cache.json":
                path = os.path.join(root, f)
                try:
                    with open(path, encoding="utf-8") as fp:
                        data = json.load(fp)
                    if not data.get("ui_pattern"):
                        all_files.append(path)
                except Exception:
                    continue
    return all_files

# ── 파일 자동 태깅 ─────────────────────────────────────────
def auto_tag_file(service, json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    png_path = json_path.replace('.json', '.png')
    print(f"\n📸 {data['app']} / {data['collected_month']} / {data['file']}")

    if not os.path.exists(png_path):
        print(f"  ⚠️  PNG 파일 없음: {png_path}")
        return

    print(f"  🤖 Claude Vision 분석 중...")
    try:
        result = analyze_image(png_path, data['app'])
    except Exception as e:
        print(f"  ❌ 분석 실패: {e}")
        return

    suggested_patterns = result.get("ui_pattern", [])
    suggested_notes    = result.get("notes", "")
    reason             = result.get("reason", "")

    print(f"\n  💡 Claude 추천:")
    print(f"     ui_pattern : {suggested_patterns}")
    print(f"     notes      : {suggested_notes}")
    print(f"     판단 근거  : {reason}")

    print()
    print("사용 가능한 ui_pattern:")
    for i, s in enumerate(UI_PATTERNS, 1):
        print(f"  {i:2}. {s}")

    print()
    raw = input(f"ui_pattern 확인/수정 (엔터 시 추천값 사용 {suggested_patterns}): ").strip()
    if raw:
        ui_pattern = []
        for token in parse_tokens(raw):
            if token.isdigit() and 1 <= int(token) <= len(UI_PATTERNS):
                ui_pattern.append(UI_PATTERNS[int(token) - 1])
            elif token in UI_PATTERNS:
                ui_pattern.append(token)
        ui_pattern = list(dict.fromkeys(ui_pattern)) or suggested_patterns
    else:
        ui_pattern = suggested_patterns

    if not ui_pattern:
        print("  ⚠️  ui_pattern이 비어있어요. 저장을 건너뜁니다.")
        return

    notes_raw = input(f"notes 확인/수정 (엔터 시 추천값 사용: {suggested_notes}): ").strip()
    notes = notes_raw if notes_raw else suggested_notes

    print(f"\n  최종 저장:")
    print(f"  ui_pattern : {ui_pattern}")
    print(f"  notes      : {notes}")

    data["ui_pattern"] = ui_pattern
    data["notes"]      = notes

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    success = update_drive_json(service, json_path, data['category'], data['app'], data['collected_month'])

    if success:
        try:
            if os.path.exists(png_path):
                os.remove(png_path)
            os.remove(json_path)
            print(f"  🗑️  로컬 파일 삭제 완료!")
            cleanup_empty_dirs(json_path)
        except Exception as e:
            print(f"  ⚠️  로컬 삭제 실패: {e}")

# ── 메인 ───────────────────────────────────────────────────
def main():
    print("=" * 42)
    print("  자동 태깅 도구 (Claude Vision)")
    print("=" * 42)

    try:
        service = get_drive_service()
    except Exception as e:
        print(f"\n❌ Drive 연결 실패: {e}")
        return

    files = find_untagged()
    if not files:
        print(f"\n✅ 미태깅 파일이 없어요!")
        return

    print(f"\n📂 미태깅 파일 {len(files)}개:")
    for i, path in enumerate(files, 1):
        rel = os.path.relpath(path, BASE_DIR)
        print(f"  {i:2}. {rel}")

    print()
    try:
        raw = input("태깅할 번호 입력 (전체: all, 예: 1 3 5): ").strip()
    except KeyboardInterrupt:
        print("\n종료.")
        return

    selected = files if raw.lower() == "all" else [
        files[int(t) - 1] for t in raw.split()
        if t.isdigit() and 1 <= int(t) <= len(files)
    ]

    if not selected:
        print("  ⚠️  선택된 파일이 없어요.")
        return

    for path in selected:
        auto_tag_file(service, path)

    print(f"\n🎉 총 {len(selected)}개 완료!")

if __name__ == "__main__":
    main()