import cv2
import numpy as np

from .vision_pipeline import buildRedMaskFromBgr


def uniquePoints(points, tol=4.0):
    out = []
    tol2 = tol * tol
    for p in points:
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > tol2 for q in out):
            out.append(p)
    return out


def lineBoxIntersections(x0, y0, vx, vy, w, h, pad=2.0):
    pts = []

    if abs(vx) > 1e-6:
        for x in (0.0, float(w - 1)):
            t = (x - x0) / vx
            y = y0 + t * vy
            if -pad <= y <= (h - 1) + pad:
                pts.append((x, min(max(y, 0.0), float(h - 1))))

    if abs(vy) > 1e-6:
        for y in (0.0, float(h - 1)):
            t = (y - y0) / vy
            x = x0 + t * vx
            if -pad <= x <= (w - 1) + pad:
                pts.append((min(max(x, 0.0), float(w - 1)), y))

    return uniquePoints(pts, tol=4.0)


def boundaryHitFromPoint(point, w, h):
    x, y = point
    max_x = float(w - 1)
    max_y = float(h - 1)

    distances = [
        abs(y),
        abs(x - max_x),
        abs(y - max_y),
        abs(x),
    ]
    edge = int(np.argmin(distances))

    if edge == 0:
        px = min(max(float(x), 0.0), max_x)
        py = 0.0
        edge_t = px / max(max_x, 1.0)
    elif edge == 1:
        px = max_x
        py = min(max(float(y), 0.0), max_y)
        edge_t = py / max(max_y, 1.0)
    elif edge == 2:
        px = min(max(float(x), 0.0), max_x)
        py = max_y
        edge_t = px / max(max_x, 1.0)
    else:
        px = 0.0
        py = min(max(float(y), 0.0), max_y)
        edge_t = py / max(max_y, 1.0)

    return {
        "point": (px, py),
        "edge": edge,
        "edge_t": edge_t,
    }


def uniqueBoundaryHits(hits, tol=4.0):
    out = []
    tol2 = tol * tol
    for hit in hits:
        px, py = hit["point"]
        duplicate = False
        for old in out:
            ox, oy = old["point"]
            if (px - ox) ** 2 + (py - oy) ** 2 <= tol2:
                duplicate = True
                break
        if not duplicate:
            out.append(hit)
    return out


def boundaryEdgesForPoints(pts, w, h, margin):
    max_x = float(w - 1)
    max_y = float(h - 1)
    xs = pts[:, 0].astype(np.float32)
    ys = pts[:, 1].astype(np.float32)

    edges = set()
    if float(np.min(ys)) <= margin:
        edges.add(0)
    if float(np.min(max_x - xs)) <= margin:
        edges.add(1)
    if float(np.min(max_y - ys)) <= margin:
        edges.add(2)
    if float(np.min(xs)) <= margin:
        edges.add(3)
    return edges


def hitDistanceSquared(hit_a, hit_b):
    ax, ay = hit_a["point"]
    bx, by = hit_b["point"]
    return (ax - bx) ** 2 + (ay - by) ** 2


def lineAspectRatio(pts):
    rect = cv2.minAreaRect(pts.reshape(-1, 1, 2).astype(np.float32))
    width, height = rect[1]
    if width <= 0 or height <= 0:
        return None

    long_side = max(float(width), float(height))
    short_side = max(min(float(width), float(height)), 1.0)
    return long_side / short_side


def fitLineProjection(pts):
    points = pts.astype(np.float32)
    vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).reshape(-1)
    direction = np.array([float(vx), float(vy)], dtype=np.float32)
    direction_len = float(np.linalg.norm(direction))
    if direction_len <= 1e-6:
        return None

    direction /= direction_len
    center = np.array([float(x0), float(y0)], dtype=np.float32)
    relative_points = points - center
    projections = relative_points @ direction
    return {
        "center": center,
        "direction": direction,
        "projections": projections,
        "relative_points": relative_points,
        "vx": float(vx),
        "vy": float(vy),
        "x0": float(x0),
        "y0": float(y0),
    }


def lineBoundaryHits(pts, w, h, edge_margin, line_fit, touched_edges=None):
    intersections = lineBoxIntersections(
        line_fit["x0"],
        line_fit["y0"],
        line_fit["vx"],
        line_fit["vy"],
        w,
        h,
        pad=edge_margin,
    )
    hits = [{**boundaryHitFromPoint(point, w, h), "kind": "line"} for point in intersections]

    if touched_edges is None:
        touched_edges = boundaryEdgesForPoints(pts, w, h, edge_margin)
    filtered = [hit for hit in hits if hit["edge"] in touched_edges]
    if len(filtered) >= 2:
        hits = filtered

    return uniqueBoundaryHits(hits, tol=4.0)


def farthestHitPair(hits):
    best_pair = None
    best_distance = -1.0
    for first_index in range(len(hits)):
        for second_index in range(first_index + 1, len(hits)):
            distance = hitDistanceSquared(hits[first_index], hits[second_index])
            if distance > best_distance:
                best_distance = distance
                best_pair = (hits[first_index], hits[second_index])

    if best_pair is None:
        return [], 0.0
    return list(best_pair), best_distance ** 0.5


def detectionResult(red_mask, hits, contour, contours):
    return {
        "red_mask": red_mask,
        "endpoints": tuple(hit["point"] for hit in hits),
        "boundary_hits": hits,
        "contour": contour,
        "contours": contours,
    }


def lineHitsFromContour(pts, w, h):
    if len(pts) < 5:
        return []

    edge_margin = max(12.0, min(w, h) * 0.10)
    touched_edges = boundaryEdgesForPoints(pts, w, h, edge_margin)
    if not touched_edges:
        return []

    aspect_ratio = lineAspectRatio(pts)
    if aspect_ratio is None or aspect_ratio < 1.75:
        return []

    line_fit = fitLineProjection(pts)
    if line_fit is None:
        return []

    projections = line_fit["projections"]
    red_span = float(np.max(projections) - np.min(projections))
    min_span_ratio = 0.32 if len(touched_edges) == 1 else 0.22
    if red_span < min(w, h) * min_span_ratio:
        return []

    line_hits = lineBoundaryHits(pts, w, h, edge_margin, line_fit, touched_edges)
    if len(line_hits) < 2:
        return []

    best_pair, length = farthestHitPair(line_hits)
    if length < min(w, h) * min_span_ratio:
        return []

    return best_pair


def edgeDotHitFromContour(pts, w, h):
    max_x = float(w - 1)
    max_y = float(h - 1)
    edge_margin = max(7.0, min(w, h) * 0.045)
    touched_edges = boundaryEdgesForPoints(pts, w, h, edge_margin)
    if not touched_edges:
        return None

    xs = pts[:, 0].astype(np.float32)
    ys = pts[:, 1].astype(np.float32)
    edge_distances = [
        ys,
        max_x - xs,
        max_y - ys,
        xs,
    ]
    min_distances = [float(np.min(values)) for values in edge_distances]
    edge = int(np.argmin(min_distances))
    min_distance = min_distances[edge]

    if min_distance > edge_margin or edge not in touched_edges:
        return None

    values = edge_distances[edge]
    near_edge = pts[values <= min_distance + max(3.0, edge_margin * 0.25)]
    if len(near_edge) == 0:
        near_edge = pts

    px, py = np.mean(near_edge, axis=0)
    return {**boundaryHitFromPoint((float(px), float(py)), w, h), "kind": "point"}


def componentIsTooComplex(contour, w, h, area):
    x, y, bw, bh = cv2.boundingRect(contour)
    if bw <= 0 or bh <= 0:
        return True
    bbox_area = float(bw * bh)
    fill = area / max(bbox_area, 1.0)

    if bbox_area > 0.55 * float(w * h) and fill > 0.12:
        return True
    return False



def maskIsBusyHatching(contours, w, h) -> bool:
    infos = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 25:
            continue
        x, y, bw, bh = cv2.boundingRect(contour)
        if bw <= 0 or bh <= 0:
            continue
        infos.append((area, bw * bh, (x, y, bw, bh)))

    if len(infos) < 6:
        return False

    total_area = sum((item[0] for item in infos), 0.0)
    largest = max(item[0] for item in infos)
    xs1 = [item[2][0] for item in infos]
    ys1 = [item[2][1] for item in infos]
    xs2 = [item[2][0] + item[2][2] for item in infos]
    ys2 = [item[2][1] + item[2][3] for item in infos]
    cover_area = float((max(xs2) - min(xs1)) * (max(ys2) - min(ys1)))

    if cover_area > 0.25 * float(w * h) and largest < 0.45 * max(total_area, 1.0):
        return True
    return False


def lineHitsFromPointsLoose(pts, w, h):
    if pts is None or len(pts) < 8:
        return []

    edge_margin = max(13.0, min(w, h) * 0.11)
    aspect_ratio = lineAspectRatio(pts)
    if aspect_ratio is None or aspect_ratio < 1.65:
        return []

    line_fit = fitLineProjection(pts)
    if line_fit is None:
        return []

    rel = line_fit["relative_points"]
    projections = line_fit["projections"]
    red_span = float(np.max(projections) - np.min(projections))
    if red_span < min(w, h) * 0.24:
        return []

    perpendicular = rel - np.outer(projections, line_fit["direction"])
    median_error = float(np.median(np.linalg.norm(perpendicular, axis=1)))
    if median_error > min(w, h) * 0.055:
        return []

    hits = lineBoundaryHits(pts, w, h, edge_margin, line_fit)
    if len(hits) < 2:
        return []

    best_pair, length = farthestHitPair(hits)
    if length < min(w, h) * 0.22:
        return []
    return best_pair


def lineHitsFromPointsRelaxed(pts, w, h):
    if pts is None or len(pts) < 8:
        return []

    edge_margin = max(16.0, min(w, h) * 0.14)
    touched_edges = boundaryEdgesForPoints(pts, w, h, edge_margin)
    if not touched_edges:
        return []

    aspect_ratio = lineAspectRatio(pts)
    if aspect_ratio is None or aspect_ratio < 1.38:
        return []

    line_fit = fitLineProjection(pts)
    if line_fit is None:
        return []

    projections = line_fit["projections"]
    red_span = float(np.max(projections) - np.min(projections))
    if red_span < min(w, h) * 0.19:
        return []

    projection_bins = np.histogram(projections, bins=6)[0]
    if int(np.count_nonzero(projection_bins)) < 4:
        return []

    relative = line_fit["relative_points"]
    perpendicular = relative - np.outer(projections, line_fit["direction"])
    errors = np.linalg.norm(perpendicular, axis=1)
    if float(np.median(errors)) > min(w, h) * 0.08:
        return []
    if float(np.percentile(errors, 85)) > min(w, h) * 0.17:
        return []

    hits = lineBoundaryHits(pts, w, h, edge_margin, line_fit, touched_edges)
    if len(hits) < 2:
        return []

    best_pair, length = farthestHitPair(hits)
    if length < min(w, h) * 0.22:
        return []
    return best_pair


def recoverRelaxedLineHits(contours, w, h):
    accepted_points = []
    accepted_contours = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        area = float(cv2.contourArea(contour))
        if area < 28.0 or componentIsTooComplex(contour, w, h, area):
            continue
        accepted_contours.append(contour)
        accepted_points.append(contour.reshape(-1, 2).astype(np.float32))

    if not accepted_points:
        return [], accepted_contours
    points = np.vstack(accepted_points).astype(np.float32)
    return lineHitsFromPointsRelaxed(points, w, h), accepted_contours

def detectRedSegmentEndpoints(face_bgr: np.ndarray) -> dict | None:
    red_mask = buildRedMaskFromBgr(face_bgr)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if not contours:
        return None

    h, w = red_mask.shape[:2]
    if maskIsBusyHatching(contours, w, h):
        return None

    kept_contours = []
    line_components = []
    point_hits = []
    all_accepted_points = []

    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        area = float(cv2.contourArea(contour))
        if area < 28:
            continue
        if componentIsTooComplex(contour, w, h, area):
            continue

        kept_contours.append(contour)
        pts = contour.reshape(-1, 2).astype(np.float32)
        all_accepted_points.append(pts)

        line_hits = lineHitsFromContour(pts, w, h)
        if line_hits:
            length = hitDistanceSquared(line_hits[0], line_hits[1]) ** 0.5
            line_components.append({
                "score": 10000.0 + length + 0.01 * area,
                "hits": line_hits,
                "contour": contour,
            })
            continue

        point_hit = edgeDotHitFromContour(pts, w, h)
        if point_hit is not None:
            point_hit["area"] = area
            point_hits.append(point_hit)

    if all_accepted_points:
        all_pts = np.vstack(all_accepted_points).astype(np.float32)
        global_hits = lineHitsFromPointsLoose(all_pts, w, h)
        if global_hits:
            if not line_components:
                hits = uniqueBoundaryHits(global_hits, tol=4.0)
                return detectionResult(red_mask, hits, kept_contours[0] if kept_contours else None, kept_contours)
            best_len = max(hitDistanceSquared(item["hits"][0], item["hits"][1]) ** 0.5 for item in line_components)
            global_len = hitDistanceSquared(global_hits[0], global_hits[1]) ** 0.5
            if global_len >= 0.85 * best_len:
                hits = uniqueBoundaryHits(global_hits, tol=4.0)
                return detectionResult(red_mask, hits, kept_contours[0] if kept_contours else None, kept_contours)

    if line_components:
        line_components.sort(key=lambda item: item["score"], reverse=True)
        if len(line_components) >= 4:
            best_len = hitDistanceSquared(line_components[0]["hits"][0], line_components[0]["hits"][1]) ** 0.5
            second_len = hitDistanceSquared(line_components[1]["hits"][0], line_components[1]["hits"][1]) ** 0.5
            if best_len < 1.45 * max(second_len, 1.0):
                return None
        best = line_components[0]
        hits = uniqueBoundaryHits(best["hits"], tol=4.0)
        return detectionResult(red_mask, hits, best["contour"], kept_contours)

    if point_hits:
        if len(point_hits) > 4:
            return None
        point_hits.sort(key=lambda hit: float(hit.get("area", 0.0)), reverse=True)
        hits = uniqueBoundaryHits(point_hits, tol=5.0)
        if len(hits) > 2:
            hits, _length = farthestHitPair(hits)
        return detectionResult(red_mask, hits, kept_contours[0] if kept_contours else None, kept_contours)

    return None


def classifyFaceRedMark(face_bgr: np.ndarray) -> dict:
    red_mask = buildRedMaskFromBgr(face_bgr)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    h, w = red_mask.shape[:2]
    meaningful_contours = [
        contour
        for contour in contours
        if float(cv2.contourArea(contour)) >= 28.0
    ]
    if not meaningful_contours:
        return {
            "kind": "blank",
            "red_mask": red_mask,
            "endpoints": (),
            "boundary_hits": [],
            "contour": None,
            "contours": contours,
        }

    detection = detectRedSegmentEndpoints(face_bgr)
    if detection:
        hits = list(detection.get("boundary_hits") or [])
        hit_kinds = {hit.get("kind") for hit in hits}
        if len(hits) == 2 and hit_kinds == {"line"}:
            return {**detection, "kind": "line"}

    relaxed_hits = []
    relaxed_contours = []
    if not maskIsBusyHatching(contours, w, h):
        relaxed_hits, relaxed_contours = recoverRelaxedLineHits(contours, w, h)
    if relaxed_hits:
        contour = relaxed_contours[0] if relaxed_contours else meaningful_contours[0]
        return {
            **detectionResult(red_mask, relaxed_hits, contour, relaxed_contours or meaningful_contours),
            "kind": "line",
        }

    if not detection:
        return {
            "kind": "invalid",
            "red_mask": red_mask,
            "endpoints": (),
            "boundary_hits": [],
            "contour": None,
            "contours": meaningful_contours,
        }

    hits = list(detection.get("boundary_hits") or [])
    hit_kinds = {hit.get("kind") for hit in hits}
    if len(hits) == 1 and hit_kinds == {"point"}:
        return {**detection, "kind": "dot"}

    return {
        **detection,
        "kind": "invalid",
        "endpoints": (),
        "boundary_hits": [],
    }
