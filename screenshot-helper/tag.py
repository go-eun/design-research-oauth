import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import subprocess

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


# ── Drive에서 JSON 파일 전체 수집 (재귀) ──────────────────
def fetch_all_json_from_drive(service, folder_id):
    json_files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/json' and trashed=false",
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token,
            pageSize=1000,
        ).execute()
        json_files.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token,
            pageSize=1000,
        ).execute()
        for subfolder in resp.get('files', []):
            json_files.extend(fetch_all_json_from_drive(service, subfolder['id']))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    return json_files


def fetch_drive_metadata(service, untagged_only=False):
    """Drive에서 JSON 메타데이터 로드
    untagged_only=True: ui_pattern이 비어있는 파일만 로드
    """
    print("  Drive에서 파일 목록 불러오는 중...")
    json_files = fetch_all_json_from_drive(service, DRIVE_ROOT)
    print(f"  총 {len(json_files)}개 파일 발견. 내용 읽는 중...")
    metadata = []
    for i, f in enumerate(json_files, 1):
        try:
            content = service.files().get_media(
                fileId=f['id'], supportsAllDrives=True
            ).execute()
            data = json.loads(content.decode('utf-8'))
            data['_drive_file_id'] = f['id']
            if untagged_only and data.get('ui_pattern'):
                continue
            metadata.append(data)
        except Exception:
            pass
        print(f"  {i}/{len(json_files)} 완료...", end='\r')
    print()
    return metadata


# ── Drive JSON 직접 업데이트 ───────────────────────────────
def update_drive_json_by_id(service, file_id, data):
    clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
    content = json.dumps(clean_data, ensure_ascii=False, indent=2).encode('utf-8')
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype='application/json')
    service.files().update(
        fileId=file_id,
        media_body=media,
        supportsAllDrives=True
    ).execute()


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


def input_tags(data, edit_mode=False, json_path=None):
    print(f"\n📸 {data['app']} / {data['collected_month']} / {data['file']}")
    print(f"   캡처 시각: {data['captured_at']}")

    # 이미지 미리보기 자동 열기
    if json_path:
        png_path = json_path.replace('.json', '.png')
    else:
        png_path = None
    preview_proc = None
    if os.path.exists(png_path):
        preview_proc = subprocess.Popen(["open", "-W", png_path])

    if edit_mode:
        print(f"   현재 ui_pattern : {data.get('ui_pattern', [])}")
        print(f"   현재 notes      : {data.get('notes', '')}")
    print()
    print("사용 가능한 ui_pattern:")
    for i, s in enumerate(UI_PATTERNS, 1):
        print(f"  {i:2}. {s}")

    while True:
        print()
        try:
            raw = input("ui_pattern 입력 (번호 또는 패턴명, 예: 10 → 로그인/회원가입 | 복수: 10 33 → 로그인+추천/메인 | 건너뜀: 엔터): ").strip()
        except KeyboardInterrupt:
            if preview_proc:
                preview_proc.terminate()
            print("\n  ⏭  건너뜀")
            return None

        if not raw:
            ui_pattern = data.get('ui_pattern', [])
            break

        ui_pattern = []
        for token in parse_tokens(raw):
            if token.isdigit() and 1 <= int(token) <= len(UI_PATTERNS):
                ui_pattern.append(UI_PATTERNS[int(token) - 1])
            elif token in UI_PATTERNS:
                ui_pattern.append(token)
            else:
                print(f"  ⚠️  '{token}' 은 유효하지 않아 건너뜀")
        ui_pattern = list(dict.fromkeys(ui_pattern))

        if ui_pattern:
            print(f"  ✓ ui_pattern: {ui_pattern}")
            break
        print("  ⚠️  유효한 번호를 입력해주세요.")

    try:
        notes = input("notes (없으면 엔터): ").strip()
    except KeyboardInterrupt:
        if preview_proc:
            preview_proc.terminate()
        print("\n  ⏭  건너뜀")
        return None

        # collected_month 수정 (edit_mode에서만)
    new_month = None
    if edit_mode:
        current_month = data.get('collected_month', '')
        try:
            raw_month = input(f"collected_month 수정 (현재: {current_month}, 엔터 시 유지): ").strip()
        except KeyboardInterrupt:
            if preview_proc:
                preview_proc.terminate()
            print("\n  ⏭  건너뜀")
            return None
        if raw_month:
            import re as _re
            if _re.fullmatch(r"\d{4}\.(0[1-9]|1[0-2])", raw_month):
                new_month = raw_month
            else:
                print(f"  ⚠️  형식 오류 — yyyy.mm 형식이 아니라 변경하지 않아요")

    if preview_proc:
        preview_proc.terminate()
    return ui_pattern, notes, new_month


def tag_file(service, json_path, edit_mode=False):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    result = input_tags(data, edit_mode, json_path=json_path)
    if result is None:
        return

    ui_pattern, notes, _ = result
    original = {k: data.get(k) for k in ['ui_pattern', 'notes']}

    data["ui_pattern"] = ui_pattern
    data["notes"]      = notes

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 로컬 태깅 완료!")

    success = update_drive_json(service, json_path, data['category'], data['app'], data['collected_month'])

    if success:
        png_path = json_path.replace('.json', '.png')
        try:
            if os.path.exists(png_path):
                os.remove(png_path)
            os.remove(json_path)
            print(f"  🗑️  로컬 파일 삭제 완료!")
            cleanup_empty_dirs(json_path)
        except Exception as e:
            print(f"  ⚠️  로컬 삭제 실패: {e}")
    else:
        for k, v in original.items():
            data[k] = v
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ↩️  Drive 실패로 로컬 태깅 롤백됩니다.")


def edit_drive_file(service, data, edit_mode=True):
    result = input_tags(data, edit_mode=edit_mode)
    if result is None:
        return

    ui_pattern, notes, new_month = result
    file_id = data['_drive_file_id']
    data["ui_pattern"] = ui_pattern
    data["notes"]      = notes
    if new_month:
        data["collected_month"] = new_month

    try:
        update_drive_json_by_id(service, file_id, data)
        print(f"  ✅ Drive 수정 완료!")
        if not edit_mode:
            print(f"  ☁️  Drive 태깅 완료! (로컬 파일 없음)")
    except Exception as e:
        print(f"  ❌ Drive 수정 실패: {e}")


def main():
    print("=" * 42)
    print("  디자인 리서치 태깅 도구")
    print("=" * 42)

    try:
        service = get_drive_service()
    except Exception as e:
        print(f"\n❌ Drive 연결 실패: {e}")
        return

    print("\n모드를 선택해주세요:")
    print("  1. 로컬 미태깅 파일 태깅")
    print("  2. Drive 태깅 파일 수정")
    print("  3. Drive 미태깅 파일 태깅")
    print("  4. Drive 파일 삭제")

    try:
        mode = input("\n번호 입력: ").strip()
    except KeyboardInterrupt:
        print("\n종료.")
        return

    # ── 모드 1: 미태깅 파일 태깅 ────────────────────────────
    if mode == "1":
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
            tag_file(service, path)

    # ── 모드 2: Drive 태깅 파일 수정 ────────────────────────
    elif mode == "2":
        all_metadata = fetch_drive_metadata(service)
        tagged = [m for m in all_metadata if m.get('ui_pattern')]

        if not tagged:
            print(f"\n✅ 태깅된 파일이 없어요!")
            return

        print(f"\n📂 Drive 태깅 파일 {len(tagged)}개:")
        for i, m in enumerate(tagged, 1):
            ui_pattern = ', '.join(m.get('ui_pattern', []))
            print(f"  {i:2}. {m['app']} / {ui_pattern} / {m['collected_month']}")
            print(f"       {m['file']}")

        print()
        try:
            raw = input("수정할 번호 입력 (전체: all, 예: 1 3 5): ").strip()
        except KeyboardInterrupt:
            print("\n종료.")
            return

        selected = tagged if raw.lower() == "all" else [
            tagged[int(t) - 1] for t in raw.split()
            if t.isdigit() and 1 <= int(t) <= len(tagged)
        ]

        if not selected:
            print("  ⚠️  선택된 파일이 없어요.")
            return

        for data in selected:
            edit_drive_file(service, data, edit_mode=True)

    # ── 모드 3: Drive 미태깅 파일 태깅 ──────────────────────
    elif mode == "3":
        untagged = fetch_drive_metadata(service, untagged_only=True)

        if not untagged:
            print(f"\n✅ 미태깅 파일이 없어요!")
            return

        print(f"\n📂 Drive 미태깅 파일 {len(untagged)}개:")
        for i, m in enumerate(untagged, 1):
            print(f"  {i:2}. {m['app']} / {m['collected_month']}")
            print(f"       {m['file']}")

        print()
        try:
            raw = input("태깅할 번호 입력 (전체: all, 예: 1 3 5): ").strip()
        except KeyboardInterrupt:
            print("\n종료.")
            return

        selected = untagged if raw.lower() == "all" else [
            untagged[int(t) - 1] for t in raw.split()
            if t.isdigit() and 1 <= int(t) <= len(untagged)
        ]

        if not selected:
            print("  ⚠️  선택된 파일이 없어요.")
            return

        for data in selected:
            edit_drive_file(service, data, edit_mode=False)

    # ── 모드 4: Drive 파일 삭제 ──────────────────────────────
    elif mode == "4":
        all_metadata = fetch_drive_metadata(service)

        if not all_metadata:
            print(f"\n✅ 파일이 없어요!")
            return

        print(f"\n📂 Drive 파일 {len(all_metadata)}개:")
        for i, m in enumerate(all_metadata, 1):
            ui_pattern = ', '.join(m.get('ui_pattern', [])) or '미태깅'
            print(f"  {i:2}. {m['app']} / {ui_pattern} / {m['collected_month']}")
            print(f"       {m['file']}")

        print()
        try:
            raw = input("삭제할 번호 입력 (예: 1 3 5): ").strip()
        except KeyboardInterrupt:
            print("\n종료.")
            return

        selected = [
            all_metadata[int(t) - 1] for t in raw.split()
            if t.isdigit() and 1 <= int(t) <= len(all_metadata)
        ]

        if not selected:
            print("  ⚠️  선택된 파일이 없어요.")
            return

        for m in selected:
            png_name = m['file']
            json_name = png_name.replace('.png', '.json')
            print(f"\n📸 {m['app']} / {', '.join(m.get('ui_pattern', []))} / {m['file']}")
            preview_proc = None
            png_id = None
            json_id = None

            try:
                parts = [m.get('category'), m.get('app'), m.get('collected_month')]
                if not all(parts):
                    print("  ⚠️  메타데이터 불완전 → 건너뜀")
                    continue

                folder_id = DRIVE_ROOT
                for part in parts:
                    resp = service.files().list(
                        q=f"name='{part}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                        fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
                    ).execute()
                    files = resp.get('files', [])
                    if not files:
                        print(f"  ⚠️  폴더 없음: {part} → 건너뜀")
                        folder_id = None
                        break
                    folder_id = files[0]['id']

                if folder_id is None:
                    continue

                for name, target in [(png_name, 'png'), (json_name, 'json')]:
                    resp = service.files().list(
                        q=f"name='{name}' and '{folder_id}' in parents and trashed=false",
                        fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
                    ).execute()
                    files = resp.get('files', [])
                    if files:
                        if target == 'png':
                            png_id = files[0]['id']
                        else:
                            json_id = files[0]['id']
            except Exception as e:
                print(f"  ⚠️  파일 ID 탐색 실패: {e}")
                continue

            if png_id:
                tmp_path = f"/tmp/{os.path.basename(png_name)}"
                content = service.files().get_media(fileId=png_id, supportsAllDrives=True).execute()
                with open(tmp_path, 'wb') as f:
                    f.write(content)
                preview_proc = subprocess.Popen(["open", "-W", tmp_path])

            try:
                confirm = input("  삭제할까요? (y/n): ").strip().lower()
            except KeyboardInterrupt:
                if preview_proc:
                    preview_proc.terminate()
                print("\n종료.")
                return

            if preview_proc:
                preview_proc.terminate()
            if png_id and os.path.exists(f"/tmp/{png_name}"):
                os.remove(f"/tmp/{png_name}")

            if confirm == 'y':
                try:
                    if png_id:
                        service.files().delete(fileId=png_id, supportsAllDrives=True).execute()
                    # JSON은 _drive_file_id로 직접 삭제
                    drive_json_id = m.get('_drive_file_id')
                    if drive_json_id:
                        service.files().delete(fileId=drive_json_id, supportsAllDrives=True).execute()
                    print(f"  🗑️  삭제 완료!")
                    # 해시 캐시에서 제거
                    h = m.get('hash')
                    if h:
                        cache_path = os.path.join(
                            os.path.expanduser("~/workspace/design-research/screenshot-helper/captures"),
                            "hash_cache.json"
                        )
                        if os.path.exists(cache_path):
                            with open(cache_path, encoding="utf-8") as f:
                                cache = json.load(f)
                            if h in cache:
                                del cache[h]
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    json.dump(cache, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"  ❌ 삭제 실패: {e}")
            else:
                print(f"  ⏭  건너뜀")

    else:
        print("  ⚠️  올바른 번호를 입력해주세요.")
        return

    print(f"\n🎉 완료!")


if __name__ == "__main__":
    main()