import os
from collections import defaultdict
import io
import json
import hashlib
import tempfile

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

TOKEN_PATH  = os.path.expanduser("~/workspace/design-research/screenshot-helper/token.json")
DRIVE_ROOT  = '17b9qKIbvJvDzqgp_Ww696t2rIjg-0X1Y'
SCOPES      = ['https://www.googleapis.com/auth/drive']
BASE_DIR    = os.path.expanduser("~/workspace/design-research/screenshot-helper/captures")
CACHE_PATH  = os.path.join(BASE_DIR, "hash_cache.json")

def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def fetch_all_files(service, folder_id):
    result = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
            pageToken=page_token, pageSize=1000
        ).execute()
        for f in resp.get('files', []):
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                result.extend(fetch_all_files(service, f['id']))
            else:
                result.append(f)
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return result

def calc_md5_from_bytes(data):
    return hashlib.md5(data).hexdigest()

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CACHE_PATH)

def main():
    print("=" * 42)
    print("  해시 캐시 일괄 등록 스크립트")
    print("=" * 42)

    service = get_service()
    print("\nDrive 파일 목록 수집 중...")
    all_files = fetch_all_files(service, DRIVE_ROOT)

    json_files = [f for f in all_files if f['name'].endswith('.json')]
    png_files = defaultdict(list)
    for f in all_files:
        if f['name'].endswith('.png'):
            png_files[f['name']].append(f)

    print(f"JSON {len(json_files)}개 / PNG {len(png_files)}개 발견\n")

    cache = load_cache()
    updated_json = 0
    skipped = 0

    for i, jf in enumerate(json_files, 1):
        try:
            content = service.files().get_media(
                fileId=jf['id'], supportsAllDrives=True
            ).execute()
            data = json.loads(content.decode('utf-8'))
        except Exception as e:
            print(f"  ⚠️  JSON 읽기 실패: {jf['name']} — {e}")
            continue

        png_name = data.get('file', '')
        existing_hash = data.get('hash')

        if existing_hash and existing_hash in cache:
            skipped += 1
            print(f"  [{i}/{len(json_files)}] ⏭  이미 등록됨: {png_name}")
            continue

        # PNG 다운로드 → 해시 계산
        pf_list = png_files.get(png_name, [])
        if not pf_list:
            print(f"  [{i}/{len(json_files)}] ⚠️  PNG 없음: {png_name}")
            continue
        pf = pf_list[0]

        try:
            png_data = service.files().get_media(
                fileId=pf['id'], supportsAllDrives=True
            ).execute()
            md5 = calc_md5_from_bytes(png_data)
        except Exception as e:
            print(f"  [{i}/{len(json_files)}] ⚠️  PNG 다운로드 실패: {png_name} — {e}")
            continue

        # 캐시 등록
        cache[md5] = png_name
        save_cache(cache)

        # Drive JSON에 hash 필드 업데이트
        if not existing_hash:
            data['hash'] = md5
            new_content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
            media = MediaIoBaseUpload(io.BytesIO(new_content), mimetype='application/json')
            service.files().update(
                fileId=jf['id'], media_body=media, supportsAllDrives=True
            ).execute()
            updated_json += 1

        print(f"  [{i}/{len(json_files)}] ✅  {png_name} → {md5[:12]}...")

    print(f"\n🎉 완료!")
    print(f"  캐시 등록: {len(cache)}개")
    print(f"  JSON 업데이트: {updated_json}개")
    print(f"  건너뜀: {skipped}개")

if __name__ == "__main__":
    main()
