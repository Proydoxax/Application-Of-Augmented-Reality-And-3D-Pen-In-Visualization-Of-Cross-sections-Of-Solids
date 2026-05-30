from math import sqrt
from typing import TYPE_CHECKING, Any

import numpy as np
from kivy.metrics import dp

from .constants import (
    CUBE_CAMERA_DISTANCE,
    DOT_PICK_THRESHOLD,
    EDGE_PICK_THRESHOLD,
    NET_2D_COLS,
    NET_2D_GAP_RATIO,
    NET_2D_LAYOUT,
    NET_2D_ROWS,
)
from .cube_mapper import (
    canonicalTToPrintedT,
    incidentPrintedFaceEdgesForKey,
    printedEdgeVertices,
    printedTToCanonicalT,
)

class CubeNetMixin:
    center_x: float
    center_y: float
    cube_pitch: float
    cube_yaw: float
    faces: tuple
    height: float
    intersections: list[dict]
    net_2d_mode: bool
    point_erase_mode: bool
    scan_direct_edge_hit_radius: float
    scan_suggestion_hit_radius: float
    scan_verification_mode: bool
    selected_face: int | None
    split_mode: bool
    target_camera_distance: float
    width: float

    if TYPE_CHECKING:
        @staticmethod
        def canonicalEdgeKey(_v_a: int, _v_b: int) -> tuple[int, int]: ...
        @staticmethod
        def clamp01(_value: float) -> float: ...
        def clearPointEraseSelection(self): ...
        def cubeRotationMatrix(self, _pitch_deg: float, _yaw_deg: float) -> Any: ...
        def dedupeIntersectionsByGeometricPoint(self, _intersections: list[dict], _digits: int = 3) -> list[dict]: ...
        def edgeIndexForKeyOnSelectedFace(self, _edge_key) -> int | None: ...
        @staticmethod
        def edgeKeyFromFaceEdge(_face_index: int, _edge_index: int) -> tuple[int, int]: ...
        def existingSectionPointKeySet(self, _digits: int = 3) -> set: ...
        def exitSplitZoom(self): ...
        def validationMessageForUser(self, _message: str) -> str: ...
        def isEdgeMode(self) -> bool: ...
        def isFaceOrEdgeMode(self) -> bool: ...
        def isPointEraseMode(self) -> bool: ...
        def normalizeIntersectionList(self): ...
        def pointKeyForEdgeT(self, _edge_key, _t: float, _digits: int = 3) -> tuple[float, float, float] | None: ...
        @staticmethod
        def pointOnEdgeKey(_edge_key, _t: float) -> tuple[float, float, float]: ...
        def projectModelPoint(self, _point): ...
        def resetCubeEditState(self): ...
        def resetScanDragState(self): ...
        def buildScanSuggestionPlane(self) -> tuple[np.ndarray, np.ndarray] | None: ...
        def setTargetRotation(self, _rotation): ...
        def flashInvalidPlacementMessage(self, _message: str): ...
        def updateCanvas(self): ...
        def validateBasicIntersectionPlacement(self, _intersections: list[dict]) -> tuple[bool, str]: ...

    def isNetViewActive(self):
        return bool(getattr(self, "net_2d_mode", False)) and not bool(getattr(self, "split_mode", False))

    def resetNetInteractionState(self):
        self.resetScanDragState()
        self.resetCubeEditState()

    def toggleNet2dMode(self):
        if self.split_mode:
            return False
        self.normalizeIntersectionList()
        enter_net = not self.isNetViewActive()
        self.scan_verification_mode = False
        self.net_2d_mode = enter_net
        if enter_net:
            self.point_erase_mode = False
            self.clearPointEraseSelection()

        self.resetNetInteractionState()
        self.updateCanvas()
        return True

    def enterScanVerificationMode(self):
        if self.split_mode:
            self.exitSplitZoom()
        self.normalizeIntersectionList()
        self.split_mode = False
        self.point_erase_mode = False
        self.clearPointEraseSelection()
        self.scan_verification_mode = True
        self.net_2d_mode = True
        self.resetNetInteractionState()
        self.updateCanvas()
        return True

    def exitScanVerificationMode(self):
        if self.split_mode:
            return False
        self.scan_verification_mode = False
        self.net_2d_mode = False
        self.resetNetInteractionState()
        cube_rotation = self.cubeRotationMatrix(self.cube_pitch, self.cube_yaw)
        self.setTargetRotation(cube_rotation)
        self.target_camera_distance = CUBE_CAMERA_DISTANCE
        self.updateCanvas()
        return True

    def selectedFaceEdgeKeys(self):
        if self.selected_face is None:
            return []
        if self.isNetViewActive():
            return [self.netEdgeKeyFromFaceEdge(self.selected_face, edge_index) for edge_index in range(4)]
        return [self.edgeKeyFromFaceEdge(self.selected_face, edge_index) for edge_index in range(4)]

    def netEdgeKeyFromFaceEdge(self, face_index, edge_index):
        a, b = printedEdgeVertices(int(face_index), int(edge_index))
        return self.canonicalEdgeKey(a, b)

    @staticmethod
    def netFaceEdgeTToCanonicalT(face_index, edge_index, t):
        _edge_key, canonical_t = printedTToCanonicalT(int(face_index), int(edge_index), float(t))
        return canonical_t

    @staticmethod
    def canonicalTToNetFaceEdgeT(face_index, edge_index, t):
        return canonicalTToPrintedT(int(face_index), int(edge_index), float(t))

    def netEdgeIndexForKeyOnFace(self, face_index, edge_key):
        edge_key = self.canonicalEdgeKey(edge_key[0], edge_key[1])
        for edge_index in range(4):
            if self.netEdgeKeyFromFaceEdge(face_index, edge_index) == edge_key:
                return edge_index
        return None

    def netFaceEdgesForEdgeKey(self, edge_key):
        try:
            return list(incidentPrintedFaceEdgesForKey(self.canonicalEdgeKey(edge_key[0], edge_key[1])))
        except (IndexError, TypeError, ValueError):
            return []

    def primaryNetFaceEdgeForPoint(self, dot, prefer_face_index=None):
        edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])

        if prefer_face_index is not None:
            try:
                face_index = int(prefer_face_index)
                edge_index = self.netEdgeIndexForKeyOnFace(face_index, edge_key)
                if edge_index is not None:
                    return face_index, edge_index
            except (TypeError, ValueError):
                pass

        try:
            source_face = int(dot.get("source_face", -1))
            source_edge = int(dot.get("source_edge", -1))
            if (
                0 <= source_face < len(self.faces)
                and 0 <= source_edge < 4
                and self.netEdgeKeyFromFaceEdge(source_face, source_edge) == edge_key
            ):
                return source_face, source_edge
        except (KeyError, TypeError, ValueError):
            pass

        face_edges = self.netFaceEdgesForEdgeKey(edge_key)
        return face_edges[0] if face_edges else (None, None)

    def netPointScreenPositions(self, dot, prefer_face_index=None, include_all=True):
        edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
        canonical_t = float(dot["t"])

        if include_all:
            face_edges = self.netFaceEdgesForEdgeKey(edge_key)
        else:
            face_edge = self.primaryNetFaceEdgeForPoint(dot, prefer_face_index=prefer_face_index)
            face_edges = [] if face_edge == (None, None) else [face_edge]

        out = []
        for face_index, edge_index in face_edges:
            if face_index is None or edge_index is None:
                continue
            local_t = self.canonicalTToNetFaceEdgeT(face_index, edge_index, canonical_t)
            p0, p1 = self.netFaceEdgeEndpointPoints(face_index, edge_index)
            px, py = self.interpolatePointOnScreenSegment(p0, p1, local_t)
            out.append((face_index, edge_index, px, py, local_t))
        return out

    def calculateNetLayoutMetrics(self):
        margin = max(dp(14), min(self.width, self.height) * 0.05)
        gap_ratio = NET_2D_GAP_RATIO
        available_w = max(1.0, float(self.width) - 2.0 * margin)
        available_h = max(1.0, float(self.height) - 2.0 * margin)
        units_w = NET_2D_COLS + (NET_2D_COLS - 1) * gap_ratio
        units_h = NET_2D_ROWS + (NET_2D_ROWS - 1) * gap_ratio
        side = min(available_w / units_w, available_h / units_h)
        gap = side * gap_ratio
        total_w = NET_2D_COLS * side + (NET_2D_COLS - 1) * gap
        total_h = NET_2D_ROWS * side + (NET_2D_ROWS - 1) * gap
        origin_x = self.center_x - total_w / 2.0
        top_y = self.center_y + total_h / 2.0
        return origin_x, top_y, side, gap

    def netFacePolygonPoints(self, face_index):
        col, row = NET_2D_LAYOUT.get(int(face_index), (1, 1))
        origin_x, top_y, side, gap = self.calculateNetLayoutMetrics()
        x0 = origin_x + col * (side + gap)
        y_top = top_y - row * (side + gap)
        return [
            (x0, y_top),
            (x0 + side, y_top),
            (x0 + side, y_top - side),
            (x0, y_top - side),
        ]

    def netFaceEdgeEndpointPoints(self, face_index, edge_index):
        tl, tr, br, bl = self.netFacePolygonPoints(face_index)
        if edge_index == 0:
            return tl, tr
        if edge_index == 1:
            return tr, br
        if edge_index == 2:
            return bl, br
        return tl, bl

    def interpolatePointOnScreenSegment(self, p0, p1, t):
        t = self.clamp01(t)
        return (
            (1.0 - t) * float(p0[0]) + t * float(p1[0]),
            (1.0 - t) * float(p0[1]) + t * float(p1[1]),
        )

    def findNearestPointOnScreenEdge(self, pos, p0, p1):
        x, y = pos
        x0, y0 = p0
        x1, y1 = p1
        vx = float(x1) - float(x0)
        vy = float(y1) - float(y0)
        denominator = vx * vx + vy * vy
        if denominator <= 1e-8:
            local_t = 0.0
        else:
            local_t = ((float(x) - float(x0)) * vx + (float(y) - float(y0)) * vy) / denominator
        local_t = self.clamp01(local_t)
        px, py = self.interpolatePointOnScreenSegment(p0, p1, local_t)
        distance = sqrt((float(x) - px) ** 2 + (float(y) - py) ** 2)
        return local_t, distance, px, py

    def isScanDirectEditActive(self):
        return bool(
            self.isNetViewActive()
            and self.isFaceOrEdgeMode()
            and not self.isEdgeMode()
            and self.selected_face is not None
            and not self.isPointEraseMode()
        )

    def findScanEdgeHitFromTouch(self, pos, edge_key=None, max_distance=None):
        if not self.isNetViewActive():
            return None

        if edge_key is None:
            if self.selected_face is None:
                return None
            face_edges = [(int(self.selected_face), edge_index) for edge_index in range(4)]
        else:
            face_edges = self.netFaceEdgesForEdgeKey(edge_key)

        best = None
        for face_index, edge_index in face_edges:
            p0, p1 = self.netFaceEdgeEndpointPoints(face_index, edge_index)
            local_t, distance, px, py = self.findNearestPointOnScreenEdge(pos, p0, p1)
            if max_distance is not None and distance > max_distance:
                continue
            if best is None or distance < best["distance"]:
                current_edge_key = self.netEdgeKeyFromFaceEdge(face_index, edge_index)
                best = {
                    "face_index": int(face_index),
                    "edge_index": int(edge_index),
                    "edge_key": current_edge_key,
                    "local_t": local_t,
                    "canonical_t": self.netFaceEdgeTToCanonicalT(face_index, edge_index, local_t),
                    "distance": distance,
                    "x": px,
                    "y": py,
                }
        return best

    def buildScanPointFromEdgeHit(self, hit):
        edge_key = self.canonicalEdgeKey(*hit["edge_key"])
        return {
            "v0": edge_key[0],
            "v1": edge_key[1],
            "t": self.clamp01(float(hit["canonical_t"])),
            "source_face": int(hit["face_index"]),
            "source_edge": int(hit["edge_index"]),
        }

    def projectIntersectionPoint(self, dot, prefer_face_index=None):
        edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
        canonical_t = float(dot["t"])
        if self.isNetViewActive():
            positions = self.netPointScreenPositions(
                dot,
                prefer_face_index=prefer_face_index,
                include_all=False,
            )
            if positions:
                _face_index, _edge_index, px, py, _local_t = positions[0]
                return px, py

        return self.projectPointOnEdge(edge_key, canonical_t)

    def projectPointOnEdge(self, edge_key, t):
        if self.isNetViewActive() and self.selected_face is not None:
            edge_index = self.edgeIndexForKeyOnSelectedFace(edge_key)
            if edge_index is not None:
                local_t = self.canonicalTToNetFaceEdgeT(self.selected_face, edge_index, t)
                p0, p1 = self.netFaceEdgeEndpointPoints(self.selected_face, edge_index)
                return self.interpolatePointOnScreenSegment(p0, p1, local_t)
        return self.projectModelPoint(self.pointOnEdgeKey(edge_key, t))

    def projectEdgeEndpointPoints(self, edge_key):
        if self.isNetViewActive() and self.selected_face is not None:
            edge_index = self.edgeIndexForKeyOnSelectedFace(edge_key)
            if edge_index is not None:
                return self.netFaceEdgeEndpointPoints(self.selected_face, edge_index)
        return (
            self.projectPointOnEdge(edge_key, 0.0),
            self.projectPointOnEdge(edge_key, 1.0),
        )

    def scanPointSuggestionsForSelectedFace(self):
        """Suggested missing section points for the selected 2D net face."""
        if not (
            self.isNetViewActive()
            and self.isFaceOrEdgeMode()
            and not self.isEdgeMode()
            and self.selected_face is not None
        ):
            return []

        if len(self.dedupeIntersectionsByGeometricPoint(self.intersections)) >= 6:
            return []

        plane = self.buildScanSuggestionPlane()
        if plane is None:
            return []

        center, normal = plane
        center = np.array(center, dtype=float)
        normal = np.array(normal, dtype=float)
        face_index = int(self.selected_face)
        existing_keys = self.existingSectionPointKeySet(digits=3)
        seen_keys = set()
        suggestions = []

        for edge_index in range(4):
            edge_key = self.netEdgeKeyFromFaceEdge(face_index, edge_index)
            a = np.array(self.pointOnEdgeKey(edge_key, 0.0), dtype=float)
            b = np.array(self.pointOnEdgeKey(edge_key, 1.0), dtype=float)
            direction = b - a
            denominator = float(np.dot(direction, normal))
            if abs(denominator) <= 1e-8:
                continue

            canonical_t = float(np.dot(center - a, normal) / denominator)
            if canonical_t < -0.035 or canonical_t > 1.035:
                continue
            canonical_t = self.clamp01(canonical_t)

            point_key = self.pointKeyForEdgeT(edge_key, canonical_t, digits=3)
            if point_key is None:
                continue
            if point_key in existing_keys or point_key in seen_keys:
                continue
            seen_keys.add(point_key)

            local_t = self.canonicalTToNetFaceEdgeT(face_index, edge_index, canonical_t)
            p0, p1 = self.netFaceEdgeEndpointPoints(face_index, edge_index)
            px, py = self.interpolatePointOnScreenSegment(p0, p1, local_t)
            suggestions.append({
                "face_index": face_index,
                "edge_index": edge_index,
                "edge_key": edge_key,
                "canonical_t": canonical_t,
                "local_t": local_t,
                "x": px,
                "y": py,
                "point_key": point_key,
            })

        return suggestions

    def pickScanPointSuggestion(self, pos):
        x, y = pos
        best = None
        best_distance = None
        hit_radius = float(getattr(self, "scan_suggestion_hit_radius", DOT_PICK_THRESHOLD * 1.85))
        for suggestion in self.scanPointSuggestionsForSelectedFace():
            dx = float(x) - float(suggestion["x"])
            dy = float(y) - float(suggestion["y"])
            distance = sqrt(dx * dx + dy * dy)
            if distance <= hit_radius and (best is None or distance < best_distance):
                best = suggestion
                best_distance = distance
        return best

    def addSuggestedScanPoint(self, suggestion):
        if not suggestion or len(self.dedupeIntersectionsByGeometricPoint(self.intersections)) >= 6:
            return False

        edge_key = self.canonicalEdgeKey(*suggestion["edge_key"])
        canonical_t = self.clamp01(float(suggestion["canonical_t"]))
        point_key = self.pointKeyForEdgeT(edge_key, canonical_t, digits=3)
        if point_key is not None and point_key in self.existingSectionPointKeySet(digits=3):
            return False

        candidate = [dict(dot) for dot in self.intersections]
        candidate.append({
            "v0": edge_key[0],
            "v1": edge_key[1],
            "t": canonical_t,
            "source_face": int(suggestion["face_index"]),
            "source_edge": int(suggestion["edge_index"]),
        })
        candidate = self.dedupeIntersectionsByGeometricPoint(candidate)
        if len(candidate) > 6:
            return False

        self.split_mode = False
        self.intersections = candidate
        self.updateCanvas()
        return True

    def findExistingScanPointNear(self, new_dot, t_tol=0.035):
        new_edge_key = self.canonicalEdgeKey(new_dot["v0"], new_dot["v1"])
        new_point_key = self.pointKeyForEdgeT(new_edge_key, float(new_dot["t"]), digits=3)
        for dot_index, dot in enumerate(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            if edge_key == new_edge_key and abs(float(dot["t"]) - float(new_dot["t"])) <= t_tol:
                return dot_index
            if new_point_key is not None:
                point_key = self.pointKeyForEdgeT(edge_key, float(dot["t"]), digits=3)
                if point_key == new_point_key:
                    return dot_index
        return None

    def setScanPointFromHit(self, hit, dot_index=None):
        if not hit:
            return False
        if dot_index is None and len(self.dedupeIntersectionsByGeometricPoint(self.intersections)) >= 6:
            return False

        new_dot = self.buildScanPointFromEdgeHit(hit)
        if dot_index is None:
            dot_index = self.findExistingScanPointNear(new_dot)

        candidate = [dict(dot) for dot in self.intersections]
        if dot_index is not None and 0 <= int(dot_index) < len(candidate):
            candidate[int(dot_index)] = new_dot
        else:
            candidate.append(new_dot)
        candidate = self.dedupeIntersectionsByGeometricPoint(candidate)
        if len(candidate) > 6:
            return False

        ok, msg = self.validateBasicIntersectionPlacement(candidate)
        if not ok:
            self.flashInvalidPlacementMessage(self.validationMessageForUser(msg))
            return False

        self.split_mode = False
        self.intersections = candidate
        self.updateCanvas()
        return True

    def addScanPointAtTouch(self, pos):
        hit = self.findScanEdgeHitFromTouch(
            pos,
            max_distance=float(getattr(self, "scan_direct_edge_hit_radius", EDGE_PICK_THRESHOLD * 1.35)),
        )
        return self.setScanPointFromHit(hit)

    def moveScanPointToTouch(self, dot_index, pos):
        if not (0 <= int(dot_index) < len(self.intersections)):
            return False
        dot = self.intersections[int(dot_index)]
        edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
        hit = self.findScanEdgeHitFromTouch(pos, edge_key=edge_key, max_distance=None)
        return self.setScanPointFromHit(hit, dot_index=int(dot_index))
