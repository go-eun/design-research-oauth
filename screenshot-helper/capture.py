import os
import re
import time
import subprocess
import warnings
import hashlib
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

warnings.filterwarnings("ignore")

from PIL import Image, ImageChops
import Quartz

# ══════════════════════════════════════════
#  설정값
# ══════════════════════════════════════════
BASE_DIR         = os.path.expanduser("~/workspace/design-research/screenshot-helper/captures")
INTERVAL         = 0.3
CHANGE_THRESHOLD = 0.02
THRESHOLD_MAX    = 0.15

IDLE_TIME        = 0.1
CROP_TOP         = 0.15
CROP_BOTTOM      = 0.12
# ══════════════════════════════════════════

os.makedirs(BASE_DIR, exist_ok=True)
HASH_CACHE_PATH = os.path.join(BASE_DIR, "hash_cache.json")

# ──────────────────────────────────────────
#  유틸
# ──────────────────────────────────────────
def get_quicktime_window():
    wlist = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    for w in wlist:
        if "QuickTime" in w.get("kCGWindowOwnerName","") \
        and "녹화" in w.get("kCGWindowName",""):
            b = w["kCGWindowBounds"]
            return int(b["X"]), int(b["Y"]), int(b["Width"]), int(b["Height"])
    return None

def capture(bounds):
    x, y, w, h = bounds
    rect    = Quartz.CGRectMake(x, y, w, h)
    img_ref = Quartz.CGWindowListCreateImage(
        rect,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault
    )
    if img_ref is None:
        path = "/tmp/qt_cap.png"
        subprocess.run(["screencapture","-x","-R",f"{x},{y},{w},{h}", path], check=True)
        return Image.open(path).convert("RGB")
    width  = Quartz.CGImageGetWidth(img_ref)
    height = Quartz.CGImageGetHeight(img_ref)
    cs     = Quartz.CGColorSpaceCreateDeviceRGB()
    raw    = bytearray(height * width * 4)
    ctx    = Quartz.CGBitmapContextCreate(
        raw, width, height, 8, width * 4, cs,
        Quartz.kCGImageAlphaNoneSkipLast | Quartz.kCGBitmapByteOrder32Big
    )
    Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, width, height), img_ref)
    return Image.frombytes("RGB", (width, height), bytes(raw), "raw", "RGBX")

def region_content(img):
    w, h = img.size
    return img.crop((0, int(h*CROP_TOP), w, int(h*(1-CROP_BOTTOM))))

def changed_ratio(img1, img2):
    c1, c2 = region_content(img1), region_content(img2)
    d      = ImageChops.difference(c1, c2).tobytes()
    n      = c1.size[0] * c1.size[1]
    return sum(
        1 for i in range(0, len(d), 3)
        if any(d[i+j] > 10 for j in range(3))
    ) / n

CATEGORIES = {
    "finance":        "금융",
    "commerce":       "커머스/쇼핑",
    "lifestyle":      "라이프스타일",
    "entertainment":  "엔터테인먼트",
    "social":         "소셜 네트워킹",
    "health-fitness": "건강/피트니스",
    "productivity":   "생산성",
    "education":      "교육",
    "utility":        "유틸리티",
    "sports":         "스포츠",
    "music":          "음악",
    "navigation":     "내비게이션/모빌리티",
    "photo-video":    "사진/비디오",
    "business":       "비즈니스",
}

def print_categories():
    print()
    print("  ┌──────────────────┬──────────────────────┐")
    print("  │ 영문명           │ 설명                 │")
    print("  ├──────────────────┼──────────────────────┤")
    for key, label in CATEGORIES.items():
        print(f"  │ {key:<16} │ {label:<20} │")
    print("  └──────────────────┴──────────────────────┘")

def prompt_app_info():
    print("\n앱 정보를 입력해주세요.")
    print_categories()

    # 1) 카테고리
    while True:
        category = input("\n  카테고리 (영문명): ").strip()
        if category in CATEGORIES:
            break
        print(f"\n  ❌ '{category}'는 유효하지 않은 카테고리예요. 아래 목록에서 영문명을 입력해주세요.")
        print_categories()

    # 2) 앱 이름
    while True:
        app_name = input("  앱 이름 (예: 강남언니): ").strip()
        if app_name:
            break
        print("  ❌ 앱 이름을 입력해주세요.")

    # 3) 수집일 (yyyy.mm)
    while True:
        date_str = input("  수집일 (yyyy.mm 형식, 예: 2025.03): ").strip()
        if re.fullmatch(r"\d{4}\.(0[1-9]|1[0-2])", date_str):
            break
        print("  ❌ 형식이 맞지 않아요. yyyy.mm 으로 입력해주세요 (예: 2025.03).")

    # 저장 경로: captures/카테고리/앱이름/yyyy.mm/
    save_dir = os.path.join(BASE_DIR, category, app_name, date_str)
    os.makedirs(save_dir, exist_ok=True)

    label = CATEGORIES[category]
    print(f"  ✅ {label} ({category}) / {app_name} / {date_str}")
    print(f"  저장 경로: {save_dir}")
    return save_dir, category, app_name, date_str
# ──────────────────────────────────────────
#  해시 캐시
# ──────────────────────────────────────────
def load_hash_cache():
    if os.path.exists(HASH_CACHE_PATH):
        try:
            with open(HASH_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  hash_cache.json 손상 → 초기화합니다 ({e})")
            return {}
    return {}
_hash_cache = load_hash_cache()

def save_hash_cache(cache):
    tmp = HASH_CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HASH_CACHE_PATH)

def calc_md5(png_path):
    with open(png_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()
def save_img(img, prefix):
    t = time.time()
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(t)) + f"_{int(t * 1000) % 1000:03d}"
    filename = f"{prefix}_{ts}"
    png_path = os.path.join(SAVE_DIR, f"{filename}.png")
    json_path = os.path.join(SAVE_DIR, f"{filename}.json")

    # 메모리에서 MD5 계산 후 중복 체크
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    md5 = hashlib.md5(buf.read()).hexdigest()

    global _hash_cache
    if md5 in _hash_cache:
        print(f"  ⏭  중복 이미지 감지 → 건너뜀 ({_hash_cache[md5]})")
        return

    # 중복 아니면 파일 저장
    buf.seek(0)
    with open(png_path, "wb") as f:
        f.write(buf.read())
    print(f"  ✅ 저장 완료 → {png_path}")

    # JSON 메타데이터 자동 생성
    metadata = {
        "file":            f"{filename}.png",
        "captured_at":     datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "app":             APP_NAME,
        "category":        CATEGORY,
        "collected_month": DATE_STR,
        "platform":        "ios",
        "ui_pattern":      [],
        "notes":           "",
        "hash":            md5,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  📋 메타데이터 생성 → {json_path}")
    # Drive 업로드
    png_ok = upload_to_drive(png_path, CATEGORY, APP_NAME, DATE_STR)
    json_ok = upload_to_drive(json_path, CATEGORY, APP_NAME, DATE_STR)

    # 해시 캐시 저장 (두 파일 모두 성공 시에만)
    if png_ok and json_ok:
        _hash_cache[md5] = f"{filename}.png"
        save_hash_cache(_hash_cache)
    else:
        print(f"  ⚠️  업로드 실패로 캐시 저장 건너뜀")
        # PNG만 성공했을 경우 Drive에서 롤백
        if png_ok and not json_ok:
            try:
                service = get_drive_service()
                folder_id = DRIVE_ROOT
                for part in [CATEGORY, APP_NAME, DATE_STR]:
                    folder_id = get_or_create_folder(service, part, folder_id)
                resp = service.files().list(
                    q=f"name='{os.path.basename(png_path)}' and '{folder_id}' in parents and trashed=false",
                    fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
                ).execute()
                for f in resp.get('files', []):
                    service.files().delete(fileId=f['id'], supportsAllDrives=True).execute()
                print(f"  ↩️  PNG 롤백 완료")
            except Exception as e:
                print(f"  ⚠️  PNG 롤백 실패: {e}")

# ──────────────────────────────────────────
#  Google Drive 업로드
# ──────────────────────────────────────────

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_PATH = os.path.expanduser('~/workspace/design-research/screenshot-helper/token.json')
DRIVE_ROOT = '17b9qKIbvJvDzqgp_Ww696t2rIjg-0X1Y'

_drive_service = None
_folder_cache = {}

def get_drive_service():
    global _drive_service
    if _drive_service is None:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_PATH, 'w') as f:
                    f.write(creds.to_json())
            else:
                raise Exception("token.json이 만료됐어요. auth_test.py를 다시 실행해주세요.")
        _drive_service = build('drive', 'v3', credentials=creds)
    return _drive_service
def get_or_create_folder(service, name, parent_id):
    cache_key = f"{parent_id}/{name}"
    if cache_key in _folder_cache:
        return _folder_cache[cache_key]
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(
        q=query,
        fields='files(id)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    meta = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(
        body=meta,
        fields='id',
        supportsAllDrives=True
    ).execute()
    folder_id = folder['id']
    _folder_cache[cache_key] = folder_id
    return folder_id
def upload_to_drive(local_path, category, app_name, date_str):
    global _drive_service
    try:
        service = get_drive_service()
        folder_id = DRIVE_ROOT
        for part in [category, app_name, date_str]:
            folder_id = get_or_create_folder(service, part, folder_id)
        file_name = os.path.basename(local_path)
        mimetype = 'image/png' if local_path.endswith('.png') else 'application/json'
        media = MediaFileUpload(local_path, mimetype=mimetype)
        service.files().create(
            body={'name': file_name, 'parents': [folder_id]},
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        print(f"  ☁️  Drive 업로드 완료 → {category}/{app_name}/{date_str}/{file_name}")
        return True
    except Exception as e:
        print(f"  ⚠️  Drive 업로드 실패 (재시도 중...): {e}")
        try:
            _drive_service = None
            service = get_drive_service()
            folder_id = DRIVE_ROOT
            for part in [category, app_name, date_str]:
                folder_id = get_or_create_folder(service, part, folder_id)
            file_name = os.path.basename(local_path)
            mimetype = 'image/png' if local_path.endswith('.png') else 'application/json'
            media = MediaFileUpload(local_path, mimetype=mimetype)
            service.files().create(
                body={'name': file_name, 'parents': [folder_id]},
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            print(f"  ☁️  Drive 업로드 완료 (재시도 성공) → {file_name}")
            return True
        except Exception as e2:
            print(f"  ⚠️  Drive 업로드 최종 실패: {e2}")
            return False
# ══════════════════════════════════════════
#  보정
# ══════════════════════════════════════════
def run_calibration(bounds):
    print("\n[2/3] 보정 중... iPhone 고정해주세요 (3초)")
    base = []
    for i in range(3):
        base.append(capture(bounds))
        time.sleep(1)
        print(f"   {i+1}/3...")

    noise     = sum(changed_ratio(base[i], base[i+1]) for i in range(2)) / 2
    threshold = max(noise * 3, CHANGE_THRESHOLD)

    if threshold > THRESHOLD_MAX:
        print(f"\n  ⚠️  threshold={threshold:.4f} — 너무 높아요!")
        print("  원인: 보정 중 화면 움직임 또는 QuickTime 캡처 오류")
        print("  → threshold를 기본값(0.04)으로 강제 설정합니다.")
        threshold = 0.04

    print(f"   완료 ✅  threshold={threshold:.4f}")
    return threshold

# ══════════════════════════════════════════
#  메인
# ══════════════════════════════════════════
print("=" * 42)
print("  디자인 리서치 캡처 시스템 v12")
print("=" * 42)

# 0. 앱 정보 입력
SAVE_DIR, CATEGORY, APP_NAME, DATE_STR = prompt_app_info()

# 1. 윈도우 탐색
bounds = None
print("\n[1/3] QuickTime 윈도우 탐색 중...")
for _ in range(10):
    bounds = get_quicktime_window()
    if bounds: break
    time.sleep(1)

if not bounds:
    print("❌ QuickTime iPhone 미러링 윈도우를 찾을 수 없어요.")
    exit(1)

x, y, w, h = bounds
print(f"   감지 ✅  위치: ({x}, {y}, {w}, {h})")

if y < 0:
    print(f"  ℹ️  외부 모니터 감지 — 음수 y좌표({y}) → Quartz 직접 캡처 방식으로 전환")

# 2. 보정
threshold = run_calibration(bounds)

# 3. 메인 루프
print("\n[3/3] 캡처 대기 중... (종료: Ctrl+C)\n")

prev       = capture(bounds)
motion_on  = False
idle_since = None

try:
    while True:
        time.sleep(INTERVAL)
        curr = capture(bounds)
        diff = changed_ratio(prev, curr)

        if diff > threshold:
            idle_since = None
            if not motion_on:
                motion_on = True
                print("  ▶ 변화 감지 중...")
        else:
            if motion_on:
                if idle_since is None:
                    idle_since = time.time()
                if time.time() - idle_since >= IDLE_TIME:
                    print("  ■ 화면 전환 → 저장 중...")
                    save_img(curr, "screen")
                    motion_on  = False
                    idle_since = None

        prev = curr

except KeyboardInterrupt:
    print("\n\n캡처 종료.")
    print(f"저장 경로: {SAVE_DIR}")