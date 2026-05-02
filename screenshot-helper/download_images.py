import os
import json
import argparse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR   = os.path.expanduser("~/workspace/design-research/screenshot-helper")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
SCOPES     = ['https://www.googleapis.com/auth/drive']
DRIVE_ROOT = '17b9qKIbvJvDzqgp_Ww696t2rIjg-0X1Y'

# ── Drive 연결 ─────────────────────────────────────────────
def get_drive_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        else:
            raise Exception("token.json 만료. auth_test.py를 다시 실행해주세요.")
    return build('drive', 'v3', credentials=creds)

# ── PNG 파일 ID 검색 ───────────────────────────────────────
def find_png_id(service, filename, folder_id):
    """파일명으로 Drive에서 PNG ID 탐색 (재귀)"""
    # 현재 폴더에서 검색
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = resp.get('files', [])
    if files:
        return files[0]['id']

    # 하위 폴더 재귀 탐색
    resp = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    for subfolder in resp.get('files', []):
        found = find_png_id(service, filename, subfolder['id'])
        if found:
            return found
    return None

# ── 이미지 다운로드 ────────────────────────────────────────
def download_images(metadata_list, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    service = get_drive_service()
    downloaded = []

    for m in metadata_list:
        filename = m.get('file')
        if not filename:
            continue

        file_id = find_png_id(service, filename, DRIVE_ROOT)
        if not file_id:
            print(f"  ⚠️  찾을 수 없음: {filename}")
            continue

        local_path = os.path.join(output_dir, filename)
        content = service.files().get_media(fileId=file_id,
                                            supportsAllDrives=True).execute()
        with open(local_path, 'wb') as f:
            f.write(content)

        downloaded.append({
            **m,
            "local_path": local_path
        })
        print(f"  ✅ 다운로드 완료: {filename}")

    return downloaded

# ── 메인 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Drive 이미지 다운로드')
    parser.add_argument('--input',      required=True, help='search_drive.py 결과 JSON 경로')
    parser.add_argument('--output-dir', default=os.path.expanduser('~/Downloads/design-research/'), help='저장 폴더')
    parser.add_argument('--output-json', help='다운로드 결과 JSON 저장 경로')
    args = parser.parse_args()

    with open(args.input) as f:
        metadata_list = json.load(f)

    print(f"\n총 {len(metadata_list)}개 이미지 다운로드 시작...\n")
    downloaded = download_images(metadata_list, args.output_dir)
    print(f"\n완료: {len(downloaded)}/{len(metadata_list)}개 다운로드")

    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(downloaded, f, ensure_ascii=False, indent=2)
        print(f"결과 저장: {args.output_json}")

if __name__ == '__main__':
    main()
