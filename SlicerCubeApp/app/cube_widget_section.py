from math import atan2
from typing import TYPE_CHECKING, Any

import numpy as np
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp

from .constants import BOTTOM_T_LABEL_Y, CUBE_CAMERA_DISTANCE, INVALID_PLACEMENT_MESSAGE, VALID_EDGE_KEYS

class CubeSectionMixin:
    edit_dot_index: int | None
    erase_candidate_index: int | None
    erase_candidate_indices: set[int]
    faces: tuple
    intersections: list[dict]
    invalid_flash_alpha: float
    invalid_flash_text: str
    invalid_flash_event: Any
    net_2d_mode: bool
    point_erase_mode: bool
    right: float
    split_saved_camera_distance: float | None
    split_mode: bool
    split_zoom_distance: float
    target_camera_distance: float
    top: float
    width: float
    y: float

    if TYPE_CHECKING:
        @staticmethod
        def canonicalEdgeKey(_v_a: int, _v_b: int) -> tuple[int, int]: ...
        @staticmethod
        def clamp01(_value: float) -> float: ...
        @staticmethod
        def edgeKeyFromFaceEdge(_face_index: int, _edge_index: int) -> tuple[int, int]: ...
        @staticmethod
        def pointOnEdgeKey(_edge_key, _t: float) -> tuple[float, float, float]: ...
        def canonicalTToNetFaceEdgeT(self, _face_index: int, _edge_index: int, _t: float) -> float: ...
        def drawLabel(self, _text, _x, _y, _font_size: float = 16.0, _color=(1, 1, 1, 1)): ...
        def exitToCube(self): ...
        def isEdgeMode(self) -> bool: ...
        def netEdgeKeyFromFaceEdge(self, _face_index: int, _edge_index: int) -> tuple[int, int]: ...
        def netFaceEdgesForEdgeKey(self, _edge_key) -> list: ...
        def isNetViewActive(self) -> bool: ...
        def resetCubeEditState(self): ...
        def resetScanDragState(self): ...
        def calculateScanSectionPreviewBox(self): ...
        def updateCanvas(self): ...

    def validateBasicIntersectionPlacement(self, intersections):
        for dot in intersections:
            try:
                edge_key = self.canonicalEdgeKey(int(dot["v0"]), int(dot["v1"]))
                t = float(dot["t"])
            except (KeyError, TypeError, ValueError):
                return False, "Invalid dot data."

            if edge_key not in VALID_EDGE_KEYS:
                return False, "Dot is not on a cube edge."
            if not (0.0 <= t <= 1.0):
                return False, "Dot value must be between 0 and 1."

        return True, "OK"

    def sectionEntries(self):
        entries = []
        for dot in self.dedupeIntersectionsByGeometricPoint(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            entries.append({
                "edge_key": edge_key,
                "t": float(dot["t"]),
                "point": np.array(self.pointOnEdgeKey(edge_key, float(dot["t"])), dtype=float),
            })
        return entries

    @staticmethod
    def planeNormalFromPoints(points):
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                for k in range(j + 1, len(points)):
                    normal = np.cross(points[j] - points[i], points[k] - points[i])
                    normal_len = np.linalg.norm(normal)
                    if normal_len > 1e-6:
                        return normal / normal_len
        return None

    @staticmethod
    def planeSortBasis(points, center, normal):
        if points:
            u = points[0] - center
        else:
            u = np.array([1.0, 0.0, 0.0], dtype=float)

        if np.linalg.norm(u) < 1e-6:
            ref = np.array([1.0, 0.0, 0.0], dtype=float)
            if abs(float(np.dot(ref, normal))) > 0.9:
                ref = np.array([0.0, 1.0, 0.0], dtype=float)
            u = np.cross(normal, ref)

        u = u / max(float(np.linalg.norm(u)), 1e-9)
        v = np.cross(normal, u)
        v = v / max(float(np.linalg.norm(v)), 1e-9)
        return u, v

    def sortPlanarEntries(self, entries, center, normal):
        if len(entries) < 3:
            return entries

        points = [entry["point"] for entry in entries]
        u, v = self.planeSortBasis(points, center, normal)
        entries.sort(key=lambda entry: atan2(
            float(np.dot(entry["point"] - center, v)),
            float(np.dot(entry["point"] - center, u)),
        ))
        return entries

    def buildSectionGeometry(self):
        ok, msg = self.validateBasicIntersectionPlacement(self.intersections)
        if not ok:
            return None, msg

        entries = self.sectionEntries()
        if len(entries) < 3:
            return None, "At least 3 dots are needed to define a split."
        if len(entries) > 6:
            return None, "A cube cross-section can have at most 6 unique dots."

        points = [entry["point"] for entry in entries]
        center = np.mean(points, axis=0)
        normal = self.planeNormalFromPoints(points)

        if normal is None:
            return None, "Invalid placement: all points lie on one line, not on a section plane."

        for point in points:
            distance = abs(float(np.dot(point - center, normal)))
            if distance > 0.04:
                return None, "Invalid placement: dots are not coplanar, so they cannot form one cube split."

        self.sortPlanarEntries(entries, center, normal)

        return {
            "entries": entries,
            "points": [entry["point"] for entry in entries],
            "center": center,
            "normal": normal,
        }, "OK"

    @staticmethod
    def planeFromPoints(a, b, c):
        normal = np.cross(b - a, c - a)
        normal_len = np.linalg.norm(normal)
        if normal_len <= 1e-6:
            return None
        return np.array(a, dtype=float), normal / normal_len

    def buildScanSuggestionPlane(self):
        entries = self.sectionEntries()
        if len(entries) < 3:
            return None

        points = [entry["point"] for entry in entries]
        best = None
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                for k in range(j + 1, len(points)):
                    plane = self.planeFromPoints(points[i], points[j], points[k])
                    if plane is None:
                        continue
                    anchor, normal = plane
                    distances = [
                        abs(float(np.dot(point - anchor, normal)))
                        for point in points
                    ]
                    inlier_indices = [
                        index for index, distance in enumerate(distances)
                        if distance <= 0.085
                    ]
                    if len(inlier_indices) < 3:
                        continue
                    score = (
                        len(inlier_indices),
                        -sum(distances[index] for index in inlier_indices),
                        -sum(min(distance, 0.25) for distance in distances),
                    )
                    if best is None or score > best["score"]:
                        centroid = np.mean([points[index] for index in inlier_indices], axis=0)
                        center = centroid - normal * float(np.dot(centroid - anchor, normal))
                        best = {"score": score, "center": center, "normal": normal}

        if best is None:
            return None
        return best["center"], best["normal"]

    def pointKeyForEdgeT(self, edge_key, t, digits=3):
        try:
            point = self.pointOnEdgeKey(edge_key, float(t))
            return tuple(round(float(value), digits) for value in point)
        except (IndexError, TypeError, ValueError):
            return None

    def existingSectionPointKeySet(self, digits=3):
        keys = set()
        for dot in self.dedupeIntersectionsByGeometricPoint(self.intersections):
            try:
                edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
                key = self.pointKeyForEdgeT(edge_key, float(dot["t"]), digits=digits)
                if key is not None:
                    keys.add(key)
            except (KeyError, TypeError, ValueError):
                continue
        return keys

    def normalizeIntersectionPoint(self, dot):
        edge_key = self.canonicalEdgeKey(int(dot["v0"]), int(dot["v1"]))
        t = self.clamp01(float(dot["t"]))
        if (int(dot["v0"]), int(dot["v1"])) != edge_key:
            t = self.clamp01(1.0 - t)
        clean_dot = dict(dot)
        clean_dot["v0"] = edge_key[0]
        clean_dot["v1"] = edge_key[1]
        clean_dot["t"] = t
        return clean_dot, edge_key, t

    @staticmethod
    def endpointVertexForIntersectionPoint(edge_key, t, endpoint_t_tol=0.055):
        if t <= endpoint_t_tol:
            return edge_key[0]
        if t >= 1.0 - endpoint_t_tol:
            return edge_key[1]
        return None

    def dedupeIntersectionsByGeometricPoint(self, intersections, same_edge_t_tol=0.08, endpoint_t_tol=0.055):
        items = []
        for dot in intersections or []:
            try:
                clean_dot, edge_key, t = self.normalizeIntersectionPoint(dot)
                if edge_key not in VALID_EDGE_KEYS:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            items.append({
                "dot": clean_dot,
                "edge_key": edge_key,
                "t": t,
                "endpoint_vertex": self.endpointVertexForIntersectionPoint(edge_key, t, endpoint_t_tol),
            })

        clusters = []
        for item in items:
            matched = None
            for cluster in clusters:
                same_edge = [
                    old for old in cluster
                    if old["edge_key"] == item["edge_key"]
                    and abs(float(old["t"]) - float(item["t"])) <= same_edge_t_tol
                ]
                if same_edge:
                    matched = cluster
                    break

                if item["endpoint_vertex"] is not None and any(
                    old["endpoint_vertex"] == item["endpoint_vertex"] for old in cluster
                ):
                    matched = cluster
                    break

            if matched is None:
                clusters.append([item])
            else:
                matched.append(item)

        deduped = []
        for cluster in clusters:
            edge_keys = {item["edge_key"] for item in cluster}
            endpoint_vertices = {
                item["endpoint_vertex"] for item in cluster
                if item["endpoint_vertex"] is not None
            }
            representative = cluster[0]
            if len(edge_keys) == 1:
                edge_key = representative["edge_key"]
                avg_t = sum(float(item["t"]) for item in cluster) / len(cluster)
                if avg_t <= same_edge_t_tol:
                    avg_t = 0.0
                elif avg_t >= 1.0 - same_edge_t_tol:
                    avg_t = 1.0
                dot = dict(representative["dot"])
                dot["v0"] = edge_key[0]
                dot["v1"] = edge_key[1]
                dot["t"] = self.clamp01(avg_t)
                deduped.append(dot)
                continue

            if endpoint_vertices:
                vertex = sorted(endpoint_vertices)[0]
                endpoint_items = [
                    item for item in cluster
                    if item["endpoint_vertex"] == vertex
                ]
                representative = endpoint_items[0] if endpoint_items else representative
                edge_key = representative["edge_key"]
                dot = dict(representative["dot"])
                dot["v0"] = edge_key[0]
                dot["v1"] = edge_key[1]
                dot["t"] = 0.0 if edge_key[0] == vertex else 1.0
                deduped.append(dot)
                continue

            deduped.append(dict(representative["dot"]))

        return deduped

    def dedupedIntersectionList(self):
        return self.dedupeIntersectionsByGeometricPoint(self.intersections)

    def normalizeIntersectionList(self):
        self.intersections = self.dedupedIntersectionList()
        return self.intersections

    @staticmethod
    def validationMessageForUser(_msg):
        return INVALID_PLACEMENT_MESSAGE

    def flashInvalidPlacementMessage(self, text=INVALID_PLACEMENT_MESSAGE):
        self.invalid_flash_text = str(text or INVALID_PLACEMENT_MESSAGE).upper()
        self.invalid_flash_alpha = 1.0
        if self.invalid_flash_event is not None:
            self.invalid_flash_event.cancel()
        self.invalid_flash_event = Clock.schedule_interval(self.fadeInvalidFlash, 1 / 30.0)
        self.updateCanvas()

    def fadeInvalidFlash(self, _dt):
        self.invalid_flash_alpha = max(0.0, self.invalid_flash_alpha - _dt / 1.45)
        if self.invalid_flash_alpha <= 0.0:
            self.invalid_flash_text = ""
            self.invalid_flash_event = None
            self.updateCanvas()
            return False
        self.updateCanvas()
        return True

    def validationMessageBottomY(self):
        return self.y + max(dp(108), BOTTOM_T_LABEL_Y + dp(82))

    @staticmethod
    def pointLetter(index):
        index = int(index)
        if 0 <= index < 26:
            return chr(ord("A") + index)
        return str(index + 1)

    def pointLabelText(self, index, t):
        return f"{self.pointLetter(index)} {float(t):.2f}"

    @staticmethod
    def splitWarningTextIntoLines(text):
        text = str(text or "")
        if text == INVALID_PLACEMENT_MESSAGE:
            return ["INVALID PLACEMENT:", "POINTS MUST LIE ON", "THE SAME PLANE"]
        if len(text) > 34:
            words = text.split()
            lines = []
            current = ""
            for word in words:
                candidate = word if not current else current + " " + word
                if len(candidate) <= 32:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines[:3]
        return [text]

    def drawWarningText(self, text, alpha=1.0):
        lines = self.splitWarningTextIntoLines(text)

        compact_net_box = bool(self.isNetViewActive()) and hasattr(self, "calculateScanSectionPreviewBox")
        if compact_net_box:
            _section_x, _section_y, box_w, box_h, margin = self.calculateScanSectionPreviewBox()
            font_size = sp(10) if len(lines) > 1 else sp(13)
            line_gap = dp(17)
        else:
            font_size = sp(14) if len(lines) > 1 else sp(20)
            line_gap = dp(25)
            box_w = min(self.width * 0.5, dp(430))
            box_h = line_gap * len(lines) + dp(18)
            margin = dp(16)

        box_x = self.right - box_w - margin
        box_y = self.top - box_h - margin

        box_center_x = box_x + box_w / 2.0
        box_center_y = box_y + box_h / 2.0

        Color(1.0, 1.0, 1.0, min(1.0, alpha))
        RoundedRectangle(
            pos=(box_x, box_y),
            size=(box_w, box_h),
            radius=[dp(12)]
        )

        for index, line in enumerate(lines):
            y = box_center_y + line_gap * (len(lines) - 1) / 2.0 - index * line_gap

            self.drawLabel(
                line,
                box_center_x,
                y,
                font_size=font_size,
                color=(1.0, 0.0, 0.0, alpha),
            )

    def drawInvalidPlacementFlash(self):
        if not self.invalid_flash_text or self.invalid_flash_alpha <= 0.0:
            return
        self.drawWarningText(self.invalid_flash_text, alpha=self.invalid_flash_alpha)

    def enterSplitZoom(self):
        if self.split_saved_camera_distance is None:
            self.split_saved_camera_distance = float(self.target_camera_distance)
        self.target_camera_distance = float(self.split_zoom_distance)

    def exitSplitZoom(self):
        restore_distance = self.split_saved_camera_distance
        self.split_saved_camera_distance = None
        if restore_distance is None:
            restore_distance = CUBE_CAMERA_DISTANCE
        self.target_camera_distance = float(restore_distance)

    def validateSplitDefinition(self):
        geom, msg = self.buildSectionGeometry()
        return geom is not None, msg

    def hasInvalidPlacementWarning(self):
        if self.split_mode:
            return False
        if self.invalid_flash_text and self.invalid_flash_alpha > 0.0:
            return True
        if len(self.intersections) < 3:
            return False
        ok, _msg = self.validateSplitDefinition()
        return not ok

    def toggleSplitMode(self):
        if self.split_mode:
            self.split_mode = False
            self.exitSplitZoom()
            self.updateCanvas()
            return True, "Cube restored."

        if self.net_2d_mode:
            return False, "Return to cube view before splitting."

        geom, msg = self.buildSectionGeometry()
        if geom is None:
            self.flashInvalidPlacementMessage(self.validationMessageForUser(msg))
            self.updateCanvas()
            return False, msg

        self.resetCubeEditState()
        self.split_mode = True
        self.enterSplitZoom()
        self.updateCanvas()
        return True, "Cube split."

    def setSplitMode(self, enabled: bool):
        if enabled:
            if self.split_mode:
                return True, "Cube already split."
            return self.toggleSplitMode()
        if self.split_mode:
            self.exitSplitZoom()
        self.split_mode = False
        self.updateCanvas()
        return True, "Cube restored."

    def undoLastPoint(self):
        if self.split_mode or not self.intersections:
            return False
        removed_index = len(self.intersections) - 1
        self.intersections.pop()
        if self.edit_dot_index is not None and self.edit_dot_index >= len(self.intersections):
            self.edit_dot_index = None

        selected = set(getattr(self, "erase_candidate_indices", set()) or set())
        selected.discard(removed_index)
        selected = {int(index) for index in selected if 0 <= int(index) < len(self.intersections)}
        self.erase_candidate_indices = selected
        ordered = sorted(selected)
        self.erase_candidate_index = ordered[0] if ordered else None

        if not self.intersections:
            self.point_erase_mode = False
            self.erase_candidate_indices = set()
            self.erase_candidate_index = None

        if self.isEdgeMode():
            self.exitToCube()
        else:
            self.updateCanvas()
        return True

    def syncEraseSelectionState(self):
        selected = set(getattr(self, "erase_candidate_indices", set()) or set())
        selected = {int(index) for index in selected if 0 <= int(index) < len(self.intersections)}
        self.erase_candidate_indices = selected
        ordered = sorted(selected)
        self.erase_candidate_index = ordered[0] if ordered else None
        return len(selected)

    def clearPointEraseSelection(self):
        self.erase_candidate_index = None
        self.erase_candidate_indices = set()

    def selectedErasePointCount(self):
        return self.syncEraseSelectionState()

    def setPointEraseMode(self, enabled: bool):
        enabled = bool(enabled)
        if enabled and not self.intersections:
            return False
        self.point_erase_mode = enabled
        self.clearPointEraseSelection()
        if enabled:
            if self.split_mode:
                self.exitSplitZoom()
            self.split_mode = False
            self.resetScanDragState()
            self.resetCubeEditState()
            self.target_camera_distance = CUBE_CAMERA_DISTANCE
        self.updateCanvas()
        return True

    def clearEraseSelection(self):
        self.clearPointEraseSelection()
        self.updateCanvas()

    def removeSelectedErasePoint(self):
        selected = sorted(
            [int(index) for index in getattr(self, "erase_candidate_indices", set()) if 0 <= int(index) < len(self.intersections)],
            reverse=True,
        )
        if not selected:
            return False

        for index in selected:
            del self.intersections[index]

        self.clearPointEraseSelection()
        if not self.intersections:
            self.point_erase_mode = False
        self.updateCanvas()
        return True

    def faceEdgeIndexForEdgeKey(self, edge_key):
        edge_key = self.canonicalEdgeKey(edge_key[0], edge_key[1])
        for face_index in range(len(self.faces)):
            for edge_index in range(4):
                if self.edgeKeyFromFaceEdge(face_index, edge_index) == edge_key:
                    return face_index, edge_index
        return 0, 0

    def formatIntersectionsAsText(self):
        lines = []
        for dot in self.dedupeIntersectionsByGeometricPoint(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            face_index = dot.get("source_face")
            edge_index = dot.get("source_edge")
            try:
                face_index = int(face_index)
                edge_index = int(edge_index)
            except (TypeError, ValueError):
                face_index = None
                edge_index = None
            if (
                face_index is None
                or edge_index is None
                or not (0 <= face_index < len(self.faces))
                or not (0 <= edge_index < 4)
                or self.netEdgeKeyFromFaceEdge(face_index, edge_index) != edge_key
            ):
                face_edges = self.netFaceEdgesForEdgeKey(edge_key)
                if face_edges:
                    face_index, edge_index = face_edges[0]
                else:
                    face_index, edge_index = self.faceEdgeIndexForEdgeKey(edge_key)
            local_t = self.canonicalTToNetFaceEdgeT(face_index, edge_index, float(dot["t"]))
            lines.append(f"{face_index + 1}, {edge_index + 1}, {local_t:.3f}")
        return "\n".join(lines)
