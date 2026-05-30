import numpy as np
from itertools import combinations
from typing import Sequence

from .constants import (
    FACE_EDGE_CORNER_INDICES,
    FACE_INDEX_TO_NAME,
    FACE_NAME_TO_INDEX,
    NET_FACE_NAMES,
    PRINTED_FACE_VERTICES,
    canonicalEdgeKey,
    clamp01,
    orientedFaceEdgeVertices,
    pointOnEdgeKey,
)


def faceSize(face: dict) -> float:
    x, y, w, h = face["bbox"]
    return 0.5 * (float(w) + float(h))


def edgeVerticesFromCorners(corners: list[int], edge: int) -> tuple[int, int]:
    start_index, end_index = FACE_EDGE_CORNER_INDICES[edge % 4]
    return corners[start_index], corners[end_index]

def printedEdgeVertices(face_index: int, edge: int) -> tuple[int, int]:
    return edgeVerticesFromCorners(PRINTED_FACE_VERTICES[face_index], edge)


def cubeLocalEdgeVertices(face_index: int, edge: int) -> tuple[int, int]:
    return orientedFaceEdgeVertices(face_index, edge)

def printedTToCanonicalT(face_index: int, edge: int, t: float) -> tuple[tuple[int, int], float]:
    a, b = printedEdgeVertices(face_index, edge)
    key = canonicalEdgeKey(a, b)

    if (a, b) == key:
        canonical_t = t
    else:
        canonical_t = 1.0 - t

    return key, clamp01(canonical_t)


def canonicalTToCubeLocalT(face_index: int, edge: int, canonical_t: float) -> float:
    a, b = cubeLocalEdgeVertices(face_index, edge)
    key = canonicalEdgeKey(a, b)

    if (a, b) == key:
        local_t = canonical_t
    else:
        local_t = 1.0 - canonical_t

    return clamp01(local_t)


def incidentFaceEdgesForKey(edge_key: tuple[int, int]) -> list[tuple[int, int]]:
    out = []
    for face_index in range(6):
        for edge in range(4):
            if canonicalEdgeKey(*cubeLocalEdgeVertices(face_index, edge)) == edge_key:
                out.append((face_index, edge))
    return out


def canonicalTToPrintedT(face_index: int, edge: int, canonical_t: float) -> float:
    a, b = printedEdgeVertices(face_index, edge)
    key = canonicalEdgeKey(a, b)

    if (a, b) == key:
        printed_t = canonical_t
    else:
        printed_t = 1.0 - canonical_t

    return clamp01(printed_t)


def incidentPrintedFaceEdgesForKey(edge_key: tuple[int, int]) -> list[tuple[int, int]]:
    edge_key = canonicalEdgeKey(*edge_key)
    out = []
    for face_index in range(6):
        for edge in range(4):
            if canonicalEdgeKey(*printedEdgeVertices(face_index, edge)) == edge_key:
                out.append((face_index, edge))
    return out

def localTToCanonicalT(face_index: int, edge: int, t: float) -> tuple[tuple[int, int], float]:
    a, b = cubeLocalEdgeVertices(face_index, edge)
    key = canonicalEdgeKey(a, b)

    if (a, b) == key:
        canonical_t = t
    else:
        canonical_t = 1.0 - t

    return key, clamp01(canonical_t)

def canonicalTToLocalT(face_index: int, edge: int, canonical_t: float) -> float:
    a, b = cubeLocalEdgeVertices(face_index, edge)
    key = canonicalEdgeKey(a, b)

    if (a, b) == key:
        local_t = canonical_t
    else:
        local_t = 1.0 - canonical_t

    return clamp01(local_t)

def mergeCanonicalObservations(raw_entries: list[dict], t_tol: float = 0.18) -> list[dict]:
    if not raw_entries:
        return []
    snap_tolerance = min(0.08, max(0.0, float(t_tol)))

    groups_by_edge: dict[tuple[int, int], list[dict]] = {}
    for entry in raw_entries:
        raw_edge_key = entry.get("edge_key", ())
        if not isinstance(raw_edge_key, Sequence) or len(raw_edge_key) != 2:
            continue
        try:
            edge_key = (int(raw_edge_key[0]), int(raw_edge_key[1]))
        except (TypeError, ValueError):
            continue
        groups_by_edge.setdefault(edge_key, []).append(entry)

    merged = []
    for edge_key, group in groups_by_edge.items():
        if not group:
            continue

        weighted_sum = 0.0
        total_weight = 0.0
        for item in group:
            t = clamp01(float(item.get("canonical_t", 0.0)))
            try:
                source_t = float(item.get("source_t", 0.5))
                away_from_vertex = min(source_t, 1.0 - source_t)
            except (TypeError, ValueError):
                away_from_vertex = 0.25
            weight = 1.0 + 0.85 * away_from_vertex
            weighted_sum += weight * t
            total_weight += weight

        avg_canonical_t = weighted_sum / max(total_weight, 1e-9)

        near_zero = [item for item in group if float(item.get("canonical_t", 0.0)) <= snap_tolerance]
        near_one = [item for item in group if float(item.get("canonical_t", 0.0)) >= 1.0 - snap_tolerance]
        if near_zero and not near_one:
            avg_canonical_t = 0.0
        elif near_one and not near_zero:
            avg_canonical_t = 1.0

        merged.append(
            {
                "edge_key": edge_key,
                "canonical_t": clamp01(avg_canonical_t),
                "merged_count": len(group),
                "sources": group,
            }
        )

    merged.sort(key=lambda merged_item: (merged_item["edge_key"], merged_item["canonical_t"]))
    return merged

def clusterRowsByY(faces: list[dict], tolerance: float | None = None) -> list[list[dict]]:
    if not faces:
        return []

    sorted_faces = sorted(faces, key=lambda face: face["center"][1])

    if tolerance is None:
        size_hints = [float(face.get("size_hint", 0.0)) for face in faces if float(face.get("size_hint", 0.0)) > 0.0]
        median_size = float(np.median(size_hints)) if size_hints else 120.0
        tolerance = median_size * 0.65

    rows: list[list[dict]] = []

    for face in sorted_faces:
        cy = float(face["center"][1])
        placed = False

        for row in rows:
            avg_y = sum(float(row_face["center"][1]) for row_face in row) / len(row)
            if abs(cy - avg_y) <= tolerance:
                row.append(face)
                placed = True
                break

        if not placed:
            rows.append([face])

    for row in rows:
        row.sort(key=lambda face: float(face["center"][0]))

    rows.sort(key=lambda row_faces: sum(float(row_face["center"][1]) for row_face in row_faces) / len(row_faces))
    return rows

def buildLayoutFromSix(selected_faces: list[dict]) -> dict[str, dict] | None:
    if len(selected_faces) != 6:
        return None

    by_y = sorted(selected_faces, key=lambda f: f["center"][1])

    top = by_y[0]
    front = by_y[-1]

    remaining = by_y[1:-1]
    if len(remaining) != 4:
        return None
    back = remaining[0]
    middle_row = sorted(remaining[1:], key=lambda f: f["center"][0])
    if len(middle_row) != 3:
        return None

    left, bottom, right = middle_row

    return {
        "top": top,
        "back": back,
        "left": left,
        "bottom": bottom,
        "right": right,
        "front": front,
    }


def scoreLayout(layout: dict[str, dict]) -> float:
    top = layout["top"]
    back = layout["back"]
    left = layout["left"]
    bottom = layout["bottom"]
    right = layout["right"]
    front = layout["front"]

    tx, ty = map(float, top["center"])
    bx, by = map(float, back["center"])
    lx, ly = map(float, left["center"])
    mx, my = map(float, bottom["center"])
    rx, ry = map(float, right["center"])
    fx, fy = map(float, front["center"])

    sizes = [faceSize(face) for face in layout.values()]
    size = float(np.median(sizes)) if sizes else 1.0
    if size <= 1e-6:
        size = 1.0

    score = 0.0
    if not (ty < by < my < fy):
        score += 1000.0
    if not (lx < mx < rx):
        score += 1000.0
    score += abs(ly - my) / size
    score += abs(ry - my) / size

    center_x = np.median([tx, bx, mx, fx])
    score += abs(tx - center_x) / size
    score += abs(bx - center_x) / size
    score += abs(mx - center_x) / size
    score += abs(fx - center_x) / size

    dy1 = by - ty
    dy2 = my - by
    dy3 = fy - my
    score += abs(dy1 - dy2) / size
    score += abs(dy2 - dy3) / size

    dx1 = mx - lx
    dx2 = rx - mx
    score += abs(dx1 - dx2) / size

    score += float(np.std(sizes) / (np.mean(sizes) + 1e-6))

    return score

def assignCrossNetFaces(faces: list[dict]) -> dict[str, dict] | None:
    if len(faces) < 6:
        return None

    candidates = sorted(faces, key=lambda f: f.get("area", 0.0), reverse=True)[:14]

    best_layout = None
    best_score = float("inf")

    for combo in combinations(candidates, 6):
        layout = buildLayoutFromSix(list(combo))
        if layout is None:
            continue

        score = scoreLayout(layout)
        if score < best_score:
            best_score = score
            best_layout = layout

    if best_layout is None:
        return None

    if best_score > 40.0:
        return None

    return best_layout


def edgeAndTFromPoint(point: tuple[float, float], face_size: int) -> tuple[int, float]:
    x, y = point
    max_xy = float(face_size - 1)

    d_top = abs(y)
    d_right = abs(x - max_xy)
    d_bottom = abs(y - max_xy)
    d_left = abs(x)

    distances = [d_top, d_right, d_bottom, d_left]
    edge = int(np.argmin(distances))

    if edge == 0:
        t = x / max_xy
    elif edge == 1:
        t = y / max_xy
    elif edge == 2:
        t = x / max_xy
    else:
        t = y / max_xy

    return edge, clamp01(t)


def canonicalObservationsToEntries(observations: list[dict], t_tol: float = 0.18) -> list[dict]:
    merged = mergeCanonicalObservations(observations, t_tol=t_tol)
    entries = []

    for item in merged:
        edge_key = item["edge_key"]
        canonical_t = item["canonical_t"]
        face_edges = sorted(incidentPrintedFaceEdgesForKey(edge_key))
        if not face_edges:
            face_edges = sorted(incidentFaceEdgesForKey(edge_key))
        if not face_edges:
            continue

        preferred = None
        sources = list(item.get("sources") or [])

        def sourcePreference(candidate_source):
            try:
                st = float(candidate_source.get("source_t", 0.5))
            except (TypeError, ValueError):
                st = 0.5
            return min(st, 1.0 - st)

        sources.sort(key=sourcePreference, reverse=True)
        for source in sources:
            source_face = int(source.get("source_face_index", -1))
            source_edge = int(source.get("source_edge", -1))
            if (source_face, source_edge) in face_edges:
                preferred = (source_face, source_edge)
                break
            for face_index, edge in face_edges:
                if face_index == source_face:
                    preferred = (face_index, edge)
                    break
            if preferred is not None:
                break

        if preferred is None:
            preferred = face_edges[0]

        face_index, edge = preferred
        local_t = canonicalTToPrintedT(face_index, edge, canonical_t)
        entries.append(
            {
                "face_index": face_index,
                "face_name": FACE_INDEX_TO_NAME[face_index],
                "edge": edge,
                "t": local_t,
                "edge_key": edge_key,
                "canonical_t": canonical_t,
                "merged_count": item["merged_count"],
                "sources": list(item.get("sources") or []),
            }
        )

    entries.sort(key=lambda entry: (entry["edge_key"], entry["canonical_t"]))
    return entries


def mapDetectedPointsToEntries(assigned_faces: dict[str, dict]) -> list[dict]:
    raw_entries = []

    for face_name, face in assigned_faces.items():
        red_detection = face.get("red_detection")
        if not red_detection:
            continue

        face_size = int(face.get("warp_size", 256))
        face_index = FACE_NAME_TO_INDEX[face_name]

        hits = red_detection.get("boundary_hits") or []
        detected_points = []
        if hits:
            for hit in hits:
                detected_points.append(
                    {
                        "point": hit.get("point"),
                        "edge": int(hit["edge"]),
                        "t": float(hit["edge_t"]),
                    }
                )
        else:
            endpoints = red_detection.get("endpoints") or []
            for point in endpoints:
                edge, t = edgeAndTFromPoint(point, face_size)
                detected_points.append({"point": point, "edge": edge, "t": t})

        if not detected_points:
            continue

        for detected in detected_points:
            edge = int(detected["edge"])
            t = float(detected["t"])

            if t < -0.02 or t > 1.02:
                continue
            t = clamp01(t)
            if t <= 0.08:
                t = 0.0
            elif t >= 0.92:
                t = 1.0

            edge_key, canonical_t = printedTToCanonicalT(face_index, edge, t)

            raw_entries.append(
                {
                    "source_face_index": face_index,
                    "source_face_name": face_name,
                    "source_edge": edge,
                    "source_t": t,
                    "edge_key": edge_key,
                    "canonical_t": canonical_t,
                }
            )

    return canonicalObservationsToEntries(raw_entries, t_tol=0.18)



def entryPointXyz(entry: dict) -> tuple[float, float, float] | None:
    try:
        raw_edge_key = entry.get("edge_key", ())
        canonical_t = float(entry.get("canonical_t"))
        if not isinstance(raw_edge_key, Sequence) or len(raw_edge_key) != 2:
            return None
        edge_key = (int(raw_edge_key[0]), int(raw_edge_key[1]))
        x, y, z = pointOnEdgeKey(edge_key, canonical_t)
        return float(x), float(y), float(z)
    except (IndexError, TypeError, ValueError):
        return None


def entryPointKey(entry: dict, digits: int = 3) -> tuple[float, float, float] | None:
    point = entryPointXyz(entry)
    if point is None:
        return None
    return tuple(round(float(v), digits) for v in point)


def entryQuality(entry: dict) -> float:
    quality = float(entry.get("merged_count", 1))
    for source in entry.get("sources") or []:
        try:
            st = float(source.get("source_t", 0.5))
            quality += 0.35 * min(st, 1.0 - st)
        except (TypeError, ValueError):
            pass
    return quality


def dedupeEntriesByGeometricPoint(entries: list[dict], digits: int = 3) -> list[dict]:
    best_by_point: dict[object, dict] = {}
    order = []
    for entry in entries or []:
        key = entryPointKey(entry, digits=digits)
        if key is None:
            try:
                fallback_t = float(entry.get("canonical_t", entry.get("t", 0.0)))
            except (TypeError, ValueError):
                fallback_t = 0.0
            key = (tuple(entry.get("edge_key", ())), round(fallback_t, 3))
        if key not in best_by_point:
            best_by_point[key] = entry
            order.append(key)
            continue
        old = best_by_point[key]
        if entryQuality(entry) > entryQuality(old):
            best_by_point[key] = entry
    return [best_by_point[key] for key in order]


def planeFromThree(points: Sequence[Sequence[float]]) -> tuple[np.ndarray, np.ndarray] | None:
    p0, p1, p2 = (np.array(p, dtype=float) for p in points[:3])
    normal = np.cross(p1 - p0, p2 - p0)
    n = float(np.linalg.norm(normal))
    if n <= 1e-7:
        return None
    return p0, normal / n


def pointsAreCoplanar(points: Sequence[Sequence[float]], tol: float = 0.055) -> bool:
    if len(points) < 3:
        return False
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            for k in range(j + 1, len(points)):
                plane = planeFromThree([points[i], points[j], points[k]])
                if plane is None:
                    continue
                p0, normal = plane
                distances = [abs(float(np.dot(np.array(p, dtype=float) - p0, normal))) for p in points]
                if max(distances) <= tol:
                    return True
    return False



def fitBestPlane(points: Sequence[Sequence[float]]) -> tuple[np.ndarray, np.ndarray] | None:
    if len(points) < 3:
        return None
    arr = np.array(points, dtype=float)
    center = np.mean(arr, axis=0)
    centered = arr - center
    try:
        _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:
        return None
    if vh.shape[0] < 3:
        return None
    normal = vh[-1]
    n = float(np.linalg.norm(normal))
    if n <= 1e-8:
        return None
    return center, normal / n


def maxPlaneDistance(points: Sequence[Sequence[float]], plane: tuple[np.ndarray, np.ndarray] | None) -> float:
    if plane is None or not points:
        return float("inf")
    center, normal = plane
    return max(abs(float(np.dot(np.array(p, dtype=float) - center, normal))) for p in points)


def snapEntriesToBestPlane(entries: list[dict], max_adjust: float = 0.22) -> list[dict]:

    entries = [dict(item) for item in entries or []]
    if len(entries) < 3:
        return entries

    raw_points = [entryPointXyz(entry) for entry in entries]
    if any(point is None for point in raw_points):
        return entries
    points = [point for point in raw_points if point is not None]

    plane = fitBestPlane(points)
    if plane is None:
        return entries
    center, normal = plane

    snapped = []
    for entry, old_point in zip(entries, points):
        raw_edge_key = entry.get("edge_key", ())
        if not isinstance(raw_edge_key, Sequence) or len(raw_edge_key) != 2:
            snapped.append(entry)
            continue
        try:
            edge_key = (int(raw_edge_key[0]), int(raw_edge_key[1]))
        except (TypeError, ValueError):
            snapped.append(entry)
            continue

        a = np.array(pointOnEdgeKey(edge_key, 0.0), dtype=float)
        b = np.array(pointOnEdgeKey(edge_key, 1.0), dtype=float)
        direction = b - a
        denominator = float(np.dot(direction, normal))
        if abs(denominator) <= 1e-8:
            snapped.append(entry)
            continue

        new_t = float(np.dot(center - a, normal) / denominator)
        if new_t < -0.08 or new_t > 1.08:
            snapped.append(entry)
            continue
        new_t = clamp01(new_t)

        old_t = float(entry.get("canonical_t", new_t))

        if old_t <= 0.08 and new_t <= 0.12:
            new_t = 0.0
        elif old_t >= 0.92 and new_t >= 0.88:
            new_t = 1.0
        elif abs(new_t - old_t) > max_adjust:
            snapped.append(entry)
            continue

        entry["canonical_t"] = clamp01(new_t)
        try:
            face_index = int(entry.get("face_index", -1))
            edge = int(entry.get("edge", -1))
            if 0 <= face_index < 6 and 0 <= edge < 4:
                entry["t"] = canonicalTToPrintedT(face_index, edge, entry["canonical_t"])
        except (TypeError, ValueError):
            pass
        snapped.append(entry)

    old_distance = maxPlaneDistance(points, plane)
    new_points = [entryPointXyz(entry) for entry in snapped]
    new_plane = fitBestPlane([p for p in new_points if p is not None])
    new_distance = maxPlaneDistance([p for p in new_points if p is not None], new_plane)

    if new_distance <= old_distance + 1e-6:
        return snapped
    return entries

def filterEntriesToValidSection(entries: list[dict], max_points: int = 6, plane_tol: float = 0.055) -> list[dict]:

    entries = dedupeEntriesByGeometricPoint(list(entries or []))
    entries = snapEntriesToBestPlane(entries)
    entries = dedupeEntriesByGeometricPoint(entries)
    n = len(entries)
    if n < 3:
        return entries

    points = [entryPointXyz(entry) for entry in entries]
    valid_indices = [i for i, p in enumerate(points) if p is not None]
    if len(valid_indices) < 3:
        return entries
    valid_points = [points[index] for index in valid_indices]
    within_point_limit = n <= max_points
    all_entries_have_points = len(valid_indices) == n
    if within_point_limit and all_entries_have_points and pointsAreCoplanar(valid_points, tol=plane_tol):
        return entries

    best_combo = None
    best_score = float("-inf")
    max_size = min(max_points, len(valid_indices))

    for size in range(max_size, 2, -1):
        found_for_size = False
        for combo in combinations(valid_indices, size):
            combo_points = [points[i] for i in combo]
            if not pointsAreCoplanar(combo_points, tol=plane_tol):
                continue
            score = size * 100.0 + sum(entryQuality(entries[i]) for i in combo)
            faces = {int(entries[i].get("face_index", -1)) for i in combo}
            score += 0.5 * len(faces)
            if score > best_score:
                best_score = score
                best_combo = combo
                found_for_size = True
        if found_for_size and size >= 4:
            break

    if best_combo is None:
        return entries

    chosen = [entries[i] for i in best_combo]
    chosen.sort(key=lambda chosen_entry: (chosen_entry.get("edge_key", ()), float(chosen_entry.get("canonical_t", 0.0))))
    return chosen

def entriesToText(entries: list[dict], one_based: bool = True) -> str:

    unique_entries = []
    seen = set()

    for item in entries:
        face = int(item.get("face_index", -1))
        edge = int(item.get("edge", -1))
        t = float(item.get("t", 0.0))

        raw_edge_key = item.get("edge_key", ())
        raw_canonical_t = item.get("canonical_t", None)
        if isinstance(raw_edge_key, Sequence) and len(raw_edge_key) == 2 and raw_canonical_t is not None:
            edge_key = (int(raw_edge_key[0]), int(raw_edge_key[1]))
            canonical_t = float(raw_canonical_t)
        elif 0 <= face < 6 and 0 <= edge < 4:
            edge_key, canonical_t = printedTToCanonicalT(face, edge, t)
        else:
            edge_key = ()
            canonical_t = t

        key = (tuple(edge_key), round(float(canonical_t), 2))
        if key in seen:
            continue
        seen.add(key)
        unique_entries.append(item)

    face_output_priority = {4: 0, 1: 1, 2: 2, 5: 3, 3: 4, 0: 5}
    unique_entries.sort(
        key=lambda output_entry: (
            face_output_priority.get(int(output_entry.get("face_index", 99)), 99),
            int(output_entry.get("edge", 99)),
            float(output_entry.get("t", 0.0)),
        )
    )

    lines = []
    for item in unique_entries:
        face = int(item["face_index"])
        edge = int(item["edge"])
        t = float(item["t"])

        if one_based:
            face += 1
            edge += 1

        lines.append(f"{face}, {edge}, {t:.3f}")
    return "\n".join(lines)

def buildDetectionArrays(assigned_faces: dict[str, dict], entries: list[dict]) -> dict:
    face_quads_page = {}
    face_centers_page = {}
    line_segments_per_face = {}
    intersection_points_per_face = {}

    for face_name, face in assigned_faces.items():
        ordered_quad = face.get("ordered_quad")
        if ordered_quad is None:
            ordered_quad = face.get("quad")
        if ordered_quad is not None:
            face_quads_page[face_name] = np.array(ordered_quad, dtype=float).tolist()
        if "center" in face:
            cx, cy = face["center"]
            face_centers_page[face_name] = [float(cx), float(cy)]

        red_detection = face.get("red_detection") or {}
        endpoints = red_detection.get("endpoints")
        if endpoints:
            line_segments_per_face[face_name] = [list(map(float, point)) for point in endpoints]

        hits = red_detection.get("boundary_hits") or []
        if hits:
            intersection_points_per_face[face_name] = [
                {
                    "point": [float(hit["point"][0]), float(hit["point"][1])],
                    "edge": int(hit["edge"]),
                    "t": float(hit["edge_t"]),
                }
                for hit in hits
            ]

    return {
        "face_order": list(NET_FACE_NAMES),
        "face_quads_page": face_quads_page,
        "face_centers_page": face_centers_page,
        "line_segments_per_face": line_segments_per_face,
        "intersection_points_per_face": intersection_points_per_face,
        "entries": entries,
    }
