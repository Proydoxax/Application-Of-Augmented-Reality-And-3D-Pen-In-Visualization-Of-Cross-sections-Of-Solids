import cv2
import numpy as np


def orderQuadPoints(points: np.ndarray) -> np.ndarray:
    pts = np.array(points, dtype=np.float32)

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)

    top_left = pts[np.argmin(s)]
    bottom_right = pts[np.argmax(s)]
    top_right = pts[np.argmin(diff)]
    bottom_left = pts[np.argmax(diff)]

    return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)


def warpFace(frame_bgr: np.ndarray, quad: np.ndarray, size: int = 256) -> np.ndarray:
    ordered = orderQuadPoints(quad)
    dst = np.array(
        [
            [0, 0],
            [size - 1, 0],
            [size - 1, size - 1],
            [0, size - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(ordered, dst)
    return cv2.warpPerspective(frame_bgr, matrix, (size, size))



def expandQuad(quad: np.ndarray, pad_ratio: float = 0.08) -> np.ndarray:

    pts = np.array(quad, dtype=np.float32)
    if pts.shape != (4, 2) or pad_ratio <= 0:
        return pts
    center = np.mean(pts, axis=0)
    return center + (pts - center) * (1.0 + float(pad_ratio))


def preprocessShapeMask(shape_mask: np.ndarray) -> np.ndarray:
    mask = shape_mask.copy()
    kernel_2 = np.ones((2, 2), np.uint8)
    kernel_3 = np.ones((3, 3), np.uint8)
    kernel_5 = np.ones((5, 5), np.uint8)
    kernel_7 = np.ones((7, 7), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_2, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_5, iterations=2)
    mask = cv2.dilate(mask, kernel_3, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_7, iterations=1)
    return mask


def preprocessBlackMask(black_mask: np.ndarray) -> np.ndarray:
    return preprocessShapeMask(black_mask)


def cleanRedMaskForStructure(red_mask: np.ndarray) -> np.ndarray | None:
    if red_mask is None or red_mask.size == 0:
        return None

    mask = red_mask.copy()
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= 20:
            cleaned[labels == label] = 255

    cleaned = cv2.dilate(cleaned, kernel, iterations=1)
    return cleaned


def buildRectangleStructureMask(black_mask: np.ndarray, red_mask: np.ndarray | None = None) -> np.ndarray | None:
    if black_mask is None or black_mask.size == 0:
        return None

    structure = black_mask.copy()
    red_clean = cleanRedMaskForStructure(red_mask)
    if red_clean is not None:
        structure = cv2.bitwise_or(structure, red_clean)
    return structure


def quadPerimeterSupport(mask: np.ndarray, quad: np.ndarray, thickness: int = 9) -> float:
    if mask is None or mask.size == 0 or quad is None:
        return 0.0

    h, w = mask.shape[:2]
    pts = np.round(np.array(quad, dtype=np.float32)).astype(np.int32)
    if pts.shape != (4, 2):
        return 0.0

    perimeter = np.zeros((h, w), dtype=np.uint8)
    cv2.polylines(perimeter, [pts.reshape(-1, 1, 2)], True, 255, max(1, int(thickness)))

    support = cv2.dilate(
        (mask > 0).astype(np.uint8) * 255,
        np.ones((max(1, int(thickness)), max(1, int(thickness))), np.uint8),
        iterations=1,
    )
    perimeter_pixels = perimeter > 0
    total = int(np.count_nonzero(perimeter_pixels))
    if total <= 0:
        return 0.0
    covered = int(np.count_nonzero((support > 0) & perimeter_pixels))
    return covered / float(total)


def bboxIou(b1, b2) -> float:
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    ax1, ay1, ax2, ay2 = x1, y1, x1 + w1, y1 + h1
    bx1, by1, bx2, by2 = x2, y2, x2 + w2, y2 + h2
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = float(iw * ih)
    if inter <= 0:
        return 0.0
    union = float(w1 * h1 + w2 * h2 - inter)
    return inter / union if union > 0 else 0.0


def dedupeFaceCandidates(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda item: (-item.get("quality", 0.0), -float(item["area"])))
    kept = []
    for cand in ordered:
        cx1, cy1 = map(float, cand["center"])
        s1 = float(cand.get("size_hint", 0.0))
        duplicate = False
        for prev in kept:
            cx2, cy2 = map(float, prev["center"])
            s2 = float(prev.get("size_hint", 0.0))
            center_dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
            size_ref = max(s1, s2, 1.0)
            if center_dist <= 0.38 * size_ref or bboxIou(cand["bbox"], prev["bbox"]) >= 0.45:
                duplicate = True
                break
        if not duplicate:
            kept.append(cand)
    return kept


def candidateFromContour(contour, image_w, image_h, min_area, max_area, approx_eps_ratio=0.035, min_aspect=0.54, max_aspect=1.72):
    area = float(cv2.contourArea(contour))
    if area < min_area or area > max_area:
        return None

    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return None

    approx = cv2.approxPolyDP(contour, approx_eps_ratio * perimeter, True)
    if len(approx) == 4 and cv2.isContourConvex(approx):
        quad = approx.reshape(4, 2).astype(np.float32)
    else:
        rect = cv2.minAreaRect(contour)
        rw, rh = rect[1]
        if rw <= 0 or rh <= 0:
            return None
        rect_aspect = max(rw, rh) / max(min(rw, rh), 1.0)
        if rect_aspect > max_aspect:
            return None
        quad = cv2.boxPoints(rect).astype(np.float32)

    x, y, bw, bh = cv2.boundingRect(quad.astype(np.int32))
    if bw <= 0 or bh <= 0:
        return None
    if bw < 22 or bh < 22:
        return None

    aspect = bw / float(bh)
    if not (min_aspect <= aspect <= max_aspect):
        return None

    bbox_area = float(bw * bh)
    if bbox_area <= 0 or bbox_area > max_area:
        return None

    extent = area / bbox_area
    if extent < 0.16:
        return None

    if x + bw < 5 or y + bh < 5 or x > image_w - 5 or y > image_h - 5:
        return None

    center = tuple(np.mean(quad, axis=0))
    aspect_quality = 1.0 - min(abs(aspect - 1.0), 1.0)
    extent_quality = min(extent / 0.55, 1.0)
    quality = 0.65 * aspect_quality + 0.35 * extent_quality
    return {
        "quad": quad,
        "bbox": (x, y, bw, bh),
        "area": area,
        "center": center,
        "size_hint": 0.5 * (bw + bh),
        "quality": float(quality),
    }


def detectFaceQuads(
    black_mask: np.ndarray,
    min_area: int = 450,
    max_area_ratio: float = 0.30,
    approx_eps_ratio: float = 0.035,
    min_aspect: float = 0.54,
    max_aspect: float = 1.72,
    max_candidates: int = 18,
) -> list[dict]:
    if black_mask is None or black_mask.size == 0:
        return []

    h, w = black_mask.shape[:2]
    max_area = float(h * w * max_area_ratio)
    masks = []
    base = preprocessBlackMask(black_mask)
    masks.append(base)

    kernel_3 = np.ones((3, 3), np.uint8)
    kernel_9 = np.ones((9, 9), np.uint8)
    masks.append(cv2.morphologyEx(black_mask.copy(), cv2.MORPH_CLOSE, kernel_3, iterations=1))
    masks.append(cv2.morphologyEx(base.copy(), cv2.MORPH_CLOSE, kernel_9, iterations=1))

    candidates = []
    for mask in masks:
        for retrieval in (cv2.RETR_LIST, cv2.RETR_EXTERNAL):
            contours, _ = cv2.findContours(mask, retrieval, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                cand = candidateFromContour(
                    contour,
                    w,
                    h,
                    min_area,
                    max_area,
                    approx_eps_ratio=approx_eps_ratio,
                    min_aspect=min_aspect,
                    max_aspect=max_aspect,
                )
                if cand is not None:
                    candidates.append(cand)

    candidates = dedupeFaceCandidates(candidates)
    if not candidates:
        return []

    if len(candidates) >= 6:
        best_subset = candidates
        best_score = float("inf")
        sorted_by_quality = sorted(candidates, key=lambda c: (-c.get("quality", 0.0), -c["area"]))[:14]
        for ref in [c["size_hint"] for c in sorted_by_quality]:
            subset = [c for c in sorted_by_quality if 0.48 * ref <= c["size_hint"] <= 1.75 * ref]
            if len(subset) < 6:
                continue
            arr = np.array([c["size_hint"] for c in subset], dtype=np.float32)
            score = float(np.std(arr) / (np.mean(arr) + 1e-6)) - 0.06 * len(subset)
            if score < best_score:
                best_score = score
                best_subset = subset
        candidates = best_subset

    candidates.sort(key=lambda item: (-item.get("quality", 0.0), -float(item["area"])))
    return candidates[:max_candidates]


def detectRectangularFaceQuads(
    black_mask: np.ndarray,
    red_mask: np.ndarray | None = None,
    min_area: int = 450,
    max_area_ratio: float = 0.30,
    approx_eps_ratio: float = 0.035,
    min_aspect: float = 0.54,
    max_aspect: float = 1.72,
    max_candidates: int = 18,
) -> list[dict]:

    if black_mask is None or black_mask.size == 0:
        return []

    candidates = []

    black_candidates = detectFaceQuads(
        black_mask,
        min_area=min_area,
        max_area_ratio=max_area_ratio,
        approx_eps_ratio=approx_eps_ratio,
        min_aspect=min_aspect,
        max_aspect=max_aspect,
        max_candidates=max_candidates,
    )
    for candidate in black_candidates:
        candidate = dict(candidate)
        candidate["source"] = "black"
        candidate["black_support"] = 1.0
        candidates.append(candidate)

    structure_mask = buildRectangleStructureMask(black_mask, red_mask)
    if structure_mask is not None:
        structure_candidates = detectFaceQuads(
            structure_mask,
            min_area=min_area,
            max_area_ratio=max_area_ratio,
            approx_eps_ratio=approx_eps_ratio,
            min_aspect=min_aspect,
            max_aspect=max_aspect,
            max_candidates=max_candidates + 8,
        )
        for candidate in structure_candidates:
            candidate = dict(candidate)
            black_support = quadPerimeterSupport(black_mask, candidate.get("quad"), thickness=9)
            if black_support < 0.22:
                continue
            candidate["source"] = "structure"
            candidate["black_support"] = float(black_support)
            candidate["quality"] = float(candidate.get("quality", 0.0)) - 0.015
            candidates.append(candidate)

    candidates = dedupeFaceCandidates(candidates)
    if not candidates:
        return []

    if len(candidates) >= 6:
        best_subset = candidates
        best_score = float("inf")
        sorted_by_quality = sorted(candidates, key=lambda c: (-c.get("quality", 0.0), -c["area"]))[:18]
        for ref in [c["size_hint"] for c in sorted_by_quality]:
            subset = [c for c in sorted_by_quality if 0.50 * ref <= c["size_hint"] <= 1.65 * ref]
            if len(subset) < 6:
                continue
            arr = np.array([c["size_hint"] for c in subset], dtype=np.float32)
            score = float(np.std(arr) / (np.mean(arr) + 1e-6)) - 0.045 * len(subset)
            if score < best_score:
                best_score = score
                best_subset = subset
        candidates = best_subset

    candidates.sort(key=lambda item: (-item.get("quality", 0.0), -float(item["area"])))
    return candidates[:max_candidates]


def extractFaceWarps(frame_bgr: np.ndarray, faces: list[dict], size: int = 256) -> list[dict]:
    enriched = []
    for face in faces:
        ordered_quad = orderQuadPoints(face["quad"])
        warp_quad = expandQuad(ordered_quad, pad_ratio=0.045)
        warped = warpFace(frame_bgr, warp_quad, size=size)
        enriched.append(
            {
                **face,
                "ordered_quad": ordered_quad,
                "warp_quad": warp_quad,
                "warp_bgr": warped,
                "warp_size": size,
            }
        )
    return enriched


def estimateNetQuad(faces: list[dict], pad: float = 0.08) -> list[list[float]] | None:
    if not faces:
        return None

    all_points = np.concatenate(
        [face["ordered_quad"] if "ordered_quad" in face else face["quad"] for face in faces],
        axis=0,
    )
    rect = cv2.minAreaRect(all_points.astype(np.float32))
    (cx, cy), (w, h), angle = rect

    w *= 1.0 + pad
    h *= 1.0 + pad
    expanded_rect = ((cx, cy), (w, h), angle)
    box = cv2.boxPoints(expanded_rect)
    box = orderQuadPoints(box)
    return box.astype(float).tolist()
