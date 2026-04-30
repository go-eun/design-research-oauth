figma.showUI(__html__, { width: 300, height: 500 });

// 시작 시 저장된 토큰 불러와서 UI로 전달
(async () => {
  const token = await figma.clientStorage.getAsync('drive_token');
  figma.ui.postMessage({ type: 'init', payload: { token: token || null } });
})();

figma.ui.onmessage = async function(msg) {
  if (!msg || !msg.type) return;

  // 토큰 저장
  if (msg.type === 'save-token') {
    const token = msg.payload && msg.payload.token;
    if (token) await figma.clientStorage.setAsync('drive_token', token);
    return;
  }

  // 토큰 삭제 (만료 시 ui.js에서 요청)
  if (msg.type === 'clear-token') {
    await figma.clientStorage.deleteAsync('drive_token');
    figma.ui.postMessage({ type: 'init', payload: { token: null } });
    return;
  }

  // resize
  if (msg.type === 'resize') {
    const h = msg.payload && msg.payload.height;
    if (typeof h === 'number') figma.ui.resize(300, Math.round(h));
    return;
  }

  // add-images
  if (msg.type === 'add-images') {
    try {
    const images = msg.payload && msg.payload.images;
    console.log('[add-images] received:', images && images.length, 'images');
    if (images && images[0]) {
      console.log('[add-images] first image:', {
        id: images[0].id,
        svc: images[0].svc,
        pat: images[0].pat,
        bytesLength: images[0].bytes && images[0].bytes.length,
      });
    }
    if (!images || !images.length) {
      figma.ui.postMessage({ type: 'add-done', payload: { count: 0 } });
      return;
    }

    // 패턴별로 이미지 그룹핑
    const byPat = new Map();
    for (const img of images) {
      if (!byPat.has(img.pat)) byPat.set(img.pat, []);
      byPat.get(img.pat).push(img);
    }

    const COLS = 10;
    const IMG_W = 390;
    const IMG_H = 844;
    const GAP = 20;
    const FRAME_PAD = 40;
    const FRAME_GAP = 80;

    const viewport = figma.viewport.center;
    let frameY = null; // 첫 프레임에서 중앙 정렬로 초기화
    let frameX = null; // 첫 프레임의 x 좌표 — 이후 프레임 모두 이 x를 사용

    await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
    await figma.loadFontAsync({ family: 'Inter', style: 'Bold' });

    const lastFrames = [];

    for (const [pat, imgs] of byPat) {
      // 기존 프레임 찾기 (pluginData 태그 + 이름 일치)
      let frame = figma.currentPage.findOne(node =>
        node.type === 'FRAME' &&
        node.name === pat &&
        node.getPluginData('source') === 'design-research'
      );

      let existingImageCount = 0;

      if (frame) {
        // 기존 프레임 — 이미지 개수 카운트 (RECTANGLE만)
        existingImageCount = frame.children.filter(c => c.type === 'RECTANGLE').length;
      } else {
        // 신규 프레임 생성
        frame = figma.createFrame();
        frame.name = pat;
        frame.fills = [{ type: 'SOLID', color: { r: 0.192, g: 0.192, b: 0.259 } }];
        frame.cornerRadius = 16;
        // 신규 프레임 위치 계산
        const isFirstFrame = frameY === null;
        frame.setPluginData('source', 'design-research');

        // 라벨 텍스트 추가 (신규일 때만)
        const label = figma.createText();
        label.fontName = { family: 'Inter', style: 'Bold' };
        label.characters = pat;
        label.fontSize = 24;
        label.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }];
        label.x = FRAME_PAD;
        label.y = FRAME_PAD;
        frame.appendChild(label);
      }

      // 전체 이미지 개수로 frame 사이즈 재계산
      const totalImgs = existingImageCount + imgs.length;
      const rows = Math.ceil(totalImgs / COLS);
      const cols = Math.min(totalImgs, COLS);
      const frameW = cols * IMG_W + (cols - 1) * GAP + FRAME_PAD * 2;
      const frameH = rows * IMG_H + (rows - 1) * GAP + FRAME_PAD * 2 + 48;
      frame.resize(frameW, frameH);

      // 신규 프레임 위치 설정 (사이즈 확정 후)
      if (existingImageCount === 0 && frame.getPluginData('source') === 'design-research' && frame.x === 0 && frame.y === 0) {
        if (frameY === null) {
          // 첫 프레임 — 뷰포트 중앙
          frame.x = viewport.x - frameW / 2;
          frame.y = viewport.y - frameH / 2;
          frameX = frame.x;
          frameY = frame.y;
        } else {
          // 두 번째부터 — 첫 프레임의 x와 동일, y만 누적
          frame.x = frameX;
          frame.y = frameY;
        }
      }

      // 이미지 삽입 (기존 개수 다음 위치부터)
      for (let i = 0; i < imgs.length; i++) {
        const idx = existingImageCount + i;
        const col = idx % COLS;
        const row = Math.floor(idx / COLS);

        const figmaImg = figma.createImage(new Uint8Array(imgs[i].bytes));
        const rect = figma.createRectangle();
        rect.name = imgs[i].svc;
        rect.resize(IMG_W, IMG_H);
        rect.x = FRAME_PAD + col * (IMG_W + GAP);
        rect.y = FRAME_PAD + 48 + row * (IMG_H + GAP);
        rect.fills = [{
          type: 'IMAGE',
          scaleMode: 'FIT',
          imageHash: figmaImg.hash,
        }];
        rect.cornerRadius = 0;
        frame.appendChild(rect);
      }

      // 신규 프레임만 frameY 누적 (기존은 위치 유지)
      if (existingImageCount === 0 && frameY !== null) {
        frameY += frameH + FRAME_GAP;
      }

      lastFrames.push(frame);
    }

    figma.viewport.scrollAndZoomIntoView(lastFrames);
    figma.ui.postMessage({ type: 'add-done', payload: { count: images.length } });
    } catch (e) {
      console.error('[add-images] error:', e);
      figma.ui.postMessage({ type: 'add-error', payload: { message: e.message || 'unknown' } });
    }
    return;
  }
};
