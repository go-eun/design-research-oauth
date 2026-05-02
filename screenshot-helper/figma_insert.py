import os
import json
import argparse
import requests
import shutil
from dotenv import load_dotenv

# ── 환경변수 로드 ───────────────────────────────────────────
load_dotenv(os.path.expanduser("~/workspace/.env"))
FIGMA_TOKEN = os.getenv("FIGMA_API_KEY") or os.getenv("FIGMA_ACCESS_TOKEN")
if not FIGMA_TOKEN:
    raise EnvironmentError("FIGMA_API_KEY 또는 FIGMA_ACCESS_TOKEN이 .env에 없어요.")
HEADERS = {"X-Figma-Token": FIGMA_TOKEN}

# ── Step 1: 이미지 업로드 → imageRef 획득 ──────────────────
def upload_image(file_key, image_path):
    url = f"https://api.figma.com/v1/images/{file_key}"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            headers=HEADERS,
            files={"image": (os.path.basename(image_path), f, "image/png")},
        )
    resp.raise_for_status()
    data = resp.json()
    images = data.get("meta", {}).get("images", {})
    if not images:
        raise Exception(f"업로드 실패: {data}")
    filename = os.path.basename(image_path)
    if filename not in images:
        raise Exception(f"imageRef 없음: {filename}")
    return images[filename]

# ── Step 2: 프레임에 이미지 노드 추가 ──────────────────────
def append_image_to_frame(file_key, parent_node_id, image_ref, filename, x, y, width, height):
    url = f"https://api.figma.com/v1/files/{file_key}/nodes"
    payload = {
        "nodes": {
            parent_node_id: {
                "document": {
                    "id": parent_node_id,
                    "children": [
                        {
                            "type": "RECTANGLE",
                            "name": filename,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "fills": [
                                {
                                    "type": "IMAGE",
                                    "scaleMode": "FILL",
                                    "imageRef": image_ref,
                                }
                            ],
                        }
                    ],
                }
            }
        }
    }
    resp = requests.patch(url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    return resp.json()

# ── 메인 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Figma 이미지 삽입')
    parser.add_argument('--input',       required=True, help='download_images.py 결과 JSON 경로')
    parser.add_argument('--file-key',    required=True, help='Figma 파일 키')
    parser.add_argument('--node-id',     required=True, help='삽입할 부모 프레임 node-id (예: 2:3)')
    parser.add_argument('--width',       type=int, default=390,  help='이미지 너비 (기본: 390)')
    parser.add_argument('--height',      type=int, default=844,  help='이미지 높이 (기본: 844)')
    parser.add_argument('--gap',         type=int, default=20,   help='이미지 간격 (기본: 20)')
    parser.add_argument('--cleanup',     action='store_true',    help='삽입 후 로컬 임시 파일 삭제')
    args = parser.parse_args()

    with open(args.input) as f:
        images = json.load(f)

    print(f"\n총 {len(images)}개 이미지 Figma 삽입 시작...\n")

    success, failed = [], []
    x = 0

    for i, m in enumerate(images):
        local_path = m.get("local_path")
        filename   = m.get("file", f"image_{i}.png")

        if not local_path or not os.path.exists(local_path):
            print(f"  ⚠️  파일 없음: {filename}")
            failed.append(filename)
            continue

        try:
            image_ref = upload_image(args.file_key, local_path)
            append_image_to_frame(
                file_key=args.file_key,
                parent_node_id=args.node_id,
                image_ref=image_ref,
                filename=filename,
                x=x,
                y=0,
                width=args.width,
                height=args.height,
            )
            print(f"  ✅ 삽입 완료: {filename}")
            success.append(filename)
            x += args.width + args.gap

        except Exception as e:
            print(f"  ❌ 삽입 실패: {filename} ({e})")
            failed.append(filename)

    # ── 결과 보고 ───────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"✅ 작업 완료\n")
    print(f"삽입 성공: {len(success)}개")
    if failed:
        print(f"삽입 실패: {len(failed)}개")
        for name in failed:
            print(f"  - {name}")
    print(f"\nFigma 링크: https://www.figma.com/design/{args.file_key}")
    print(f"{'─' * 50}")

    # ── 임시 파일 정리 ──────────────────────────────────────
    if args.cleanup and images:
        tmp_dir = os.path.dirname(images[0].get("local_path", ""))
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            print(f"\n🗑️  임시 파일 삭제 완료: {tmp_dir}")

if __name__ == "__main__":
    main()
