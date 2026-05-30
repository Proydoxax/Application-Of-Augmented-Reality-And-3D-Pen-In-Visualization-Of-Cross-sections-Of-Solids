from math import atan2, sqrt
from typing import TYPE_CHECKING, Any

import numpy as np
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle
from kivy.metrics import dp, sp

from .constants import (
    ACTIVE_DOT_RADIUS,
    BOTTOM_T_LABEL_Y,
    CANVAS_FONT_NAME,
    DOT_LABEL_OFFSET,
    DOT_RADIUS,
    EDGE_LABEL_OFFSET_CUBE,
    EDGE_LABEL_OFFSET_FACE,
)

class CubeRenderMixin:
    canvas: Any
    center_x: float
    current_edge_key: tuple[int, int] | None
    current_t: float
    edges: tuple
    erase_candidate_indices: set[int]
    face_polygons: list
    faces: tuple
    front_face: int | None
    height: float
    intersections: list[dict]
    label_texture_cache: dict
    pos: tuple[float, float]
    proj_vertices: list
    selected_face: int | None
    show_coord_labels: bool
    show_edge_numbers: bool
    show_face_numbers: bool
    size: tuple[float, float]
    split_mode: bool
    width: float
    x: float
    y: float

    if TYPE_CHECKING:
        @staticmethod
        def canonicalEdgeKey(_v_a: int, _v_b: int) -> tuple[int, int]: ...
        @staticmethod
        def clamp01(_value: float) -> float: ...
        @staticmethod
        def pointOnEdgeKey(_edge_key, _t: float) -> tuple[float, float, float]: ...
        @staticmethod
        def vertexVec(_index: int) -> np.ndarray: ...
        def canonicalTToNetFaceEdgeT(self, _face_index: int, _edge_index: int, _t: float) -> float: ...
        def pointLabelText(self, _index: int, _t: float) -> str: ...
        def drawInvalidPlacementFlash(self): ...
        def drawWarningText(self, _text, _alpha: float = 1.0): ...
        def edgeIndexForKeyOnSelectedFace(self, _edge_key) -> int | None: ...
        def faceCenter(self, _face_index: int) -> tuple[float, float, float]: ...
        def validationMessageForUser(self, _message: str) -> str: ...
        def isCubeMode(self) -> bool: ...
        def isEdgeMode(self) -> bool: ...
        def isFaceOrEdgeMode(self) -> bool: ...
        def isPointEraseMode(self) -> bool: ...
        def netPointScreenPositions(
            self,
            _dot,
            _prefer_face_index=None,
            _include_all=True,
        ) -> list[tuple[int, int, float, float, float]]: ...
        def netEdgeIndexForKeyOnFace(self, _face_index: int, _edge_key) -> int | None: ...
        def netFaceEdgeEndpointPoints(self, _face_index: int, _edge_index: int) -> tuple[tuple[float, float], tuple[float, float]]: ...
        def isNetViewActive(self) -> bool: ...
        def planeSortBasis(self, _points, _center, _normal) -> tuple[np.ndarray, np.ndarray]: ...
        def pointLetter(self, _index: int) -> str: ...
        def interpolatePointOnScreenSegment(self, _p0, _p1, _t: float) -> tuple[float, float]: ...
        def projectEdgeEndpointPoints(self, _edge_key) -> tuple[tuple[float, float], tuple[float, float]]: ...
        def projectPointOnEdge(self, _edge_key, _t: float) -> tuple[float, float]: ...
        def projectPoint(self, _x: float, _y: float, _z: float) -> tuple[float, float]: ...
        def rotatePoint(self, _x: float, _y: float, _z: float) -> tuple[float, float, float]: ...
        def scanPointSuggestionsForSelectedFace(self) -> list[dict]: ...
        def buildSectionGeometry(self) -> tuple[dict[str, Any] | None, str]: ...
        def selectedFaceEdgeKeys(self) -> list[tuple[int, int]]: ...
        def sortPlanarEntries(self, _entries, _center, _normal): ...
        def updateGeometry(self): ...
        def validateSplitDefinition(self) -> tuple[bool, str]: ...

    def drawLabel(self, text, x, y, font_size: float = 16.0, color=(1, 1, 1, 1)):
        key = (str(text), int(font_size), tuple(color))
        texture = self.label_texture_cache.get(key)

        if texture is None:
            label = CoreLabel(text=str(text), font_size=font_size, color=color, font_name=CANVAS_FONT_NAME)
            label.refresh()
            texture = label.texture
            self.label_texture_cache[key] = texture

        texture_width, texture_height = texture.size
        Rectangle(
            texture=texture,
            pos=(x - texture_width / 2, y - texture_height / 2),
            size=texture.size,
        )

    def drawBackground(self):
        if self.isFaceOrEdgeMode():
            Color(0.05, 0.05, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)

    def drawEdges(self):
        if self.isNetViewActive():
            for face_index in range(len(self.faces)):
                polygon = self.face_polygons[face_index]
                selected = self.selected_face == face_index and self.isFaceOrEdgeMode()
                if selected:
                    Color(1, 1, 1, 1)
                    width = 2.6
                elif self.isFaceOrEdgeMode():
                    Color(1, 1, 1, 0.25)
                    width = 1.1
                else:
                    Color(1, 1, 1, 1)
                    width = 1.7
                flat = [coord for point in polygon for coord in point]
                Line(points=flat, width=width, close=True)
            return

        selected_face_vertices = self.faces[self.selected_face] if self.selected_face is not None else []

        for vertex_1, vertex_2 in self.edges:
            x1, y1 = self.proj_vertices[vertex_1]
            x2, y2 = self.proj_vertices[vertex_2]

            on_selected_face = vertex_1 in selected_face_vertices and vertex_2 in selected_face_vertices

            if self.isFaceOrEdgeMode():
                if on_selected_face:
                    Color(1, 1, 1, 1)
                    width = 2.5
                else:
                    Color(1, 1, 1, 0.2)
                    width = 1.0
            else:
                Color(1, 1, 1, 1)
                width = 1.5

            Line(points=[x1, y1, x2, y2], width=width)

    def drawFaceNumbers(self):
        if not self.show_face_numbers:
            return

        if self.isNetViewActive():
            for face_index, polygon in enumerate(self.face_polygons):
                cx = sum(point[0] for point in polygon) / len(polygon)
                cy = sum(point[1] for point in polygon) / len(polygon)
                if self.isFaceOrEdgeMode():
                    color = (1, 1, 1, 1) if face_index == self.selected_face else (1, 1, 1, 0.35)
                else:
                    color = (1, 1, 1, 1)
                self.drawLabel(str(face_index + 1), cx, cy, font_size=sp(19), color=color)
            return

        for face_index in range(len(self.faces)):
            cx, cy, cz = self.faceCenter(face_index)
            rx, ry, rz = self.rotatePoint(cx, cy, cz)
            px, py = self.projectPoint(rx, ry, rz)

            if self.isFaceOrEdgeMode():
                color = (1, 1, 1, 1) if face_index == self.selected_face else (1, 1, 1, 0.2)
            else:
                color = (1, 1, 1, 1) if self.front_face == face_index else (1, 1, 1, 0.2)

            self.drawLabel(str(face_index + 1), px, py, font_size=sp(18), color=color)

    def drawEdgeNumbers(self):
        if not self.show_edge_numbers:
            return

        if self.isNetViewActive():
            if self.isCubeMode():
                for face_index in range(len(self.faces)):
                    self.drawEdgeNumbersForFace(
                        face_index,
                        -EDGE_LABEL_OFFSET_CUBE * 0.55,
                        font_size=sp(12),
                    )
            elif self.selected_face is not None:
                self.drawEdgeNumbersForFace(self.selected_face, EDGE_LABEL_OFFSET_FACE * 0.55)
            return

        if self.isCubeMode():
            if self.front_face is not None:
                self.drawEdgeNumbersForFace(self.front_face, EDGE_LABEL_OFFSET_CUBE)
        elif self.selected_face is not None:
            self.drawEdgeNumbersForFace(self.selected_face, EDGE_LABEL_OFFSET_FACE)

    def intersectionColors(self, edge_key, selected_face_edge_keys):
        if self.isFaceOrEdgeMode() and self.selected_face is not None:
            belongs = edge_key in selected_face_edge_keys
            return (
                (1, 0, 0, 1) if belongs else (1, 0, 0, 0.2),
                (1, 1, 0, 1) if belongs else (1, 1, 0, 0.2),
                1.0 if belongs else 0.2,
            )
        return (1, 0, 0, 1), (1, 1, 0, 1), 1.0

    def drawIntersectionPoint(self, dot_index, x, y, dot_t, dot_color, label_color, alpha):
        radius = DOT_RADIUS
        if self.isPointEraseMode():
            radius = DOT_RADIUS * 2.2
            if dot_index in getattr(self, "erase_candidate_indices", set()):
                dot_color = (1.0, 0.85, 0.05, 1.0)
                label_color = (1.0, 0.85, 0.05, 1.0)

        Color(*dot_color)
        Ellipse(pos=(x - radius, y - radius), size=(2 * radius, 2 * radius))

        if self.show_coord_labels and alpha > 0.3:
            Color(*label_color)
            self.drawLabel(
                self.pointLabelText(dot_index, dot_t),
                x + DOT_LABEL_OFFSET,
                y + DOT_LABEL_OFFSET,
                font_size=sp(13),
                color=label_color,
            )

    def drawEdgeNumbersForFace(self, face_index, label_offset, font_size=None):
        face_vertices = self.faces[face_index]
        polygon = self.face_polygons[face_index]
        center_x = sum(point[0] for point in polygon) / len(polygon)
        center_y = sum(point[1] for point in polygon) / len(polygon)
        font_size = sp(16) if font_size is None else font_size

        for edge_index in range(4):
            if self.isNetViewActive():
                (x1, y1), (x2, y2) = self.netFaceEdgeEndpointPoints(face_index, edge_index)
            else:
                i0 = face_vertices[edge_index % 4]
                i1 = face_vertices[(edge_index + 1) % 4]

                x1, y1 = self.proj_vertices[i0]
                x2, y2 = self.proj_vertices[i1]
            mid_x = 0.5 * (x1 + x2)
            mid_y = 0.5 * (y1 + y2)

            dx = mid_x - center_x
            dy = mid_y - center_y
            length = sqrt(dx * dx + dy * dy) or 1.0

            label_x = mid_x + dx / length * label_offset
            label_y = mid_y + dy / length * label_offset

            color = (0, 1, 0, 1)
            Color(*color)
            self.drawLabel(str(edge_index + 1), label_x, label_y, font_size=font_size, color=color)

    def drawIntersections(self):
        selected_face_edge_keys = self.selectedFaceEdgeKeys() if self.selected_face is not None else []

        if self.isNetViewActive():
            face_mode = self.isFaceOrEdgeMode() and self.selected_face is not None
            for dot_index, dot in enumerate(self.intersections):
                edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
                positions = self.netPointScreenPositions(
                    dot,
                    prefer_face_index=self.selected_face if face_mode else None,
                    include_all=face_mode,
                )
                for _face_index, _edge_index, px, py, local_t in positions:
                    dot_color, label_color, alpha = self.intersectionColors(edge_key, selected_face_edge_keys)
                    self.drawIntersectionPoint(dot_index, px, py, local_t, dot_color, label_color, alpha)
            return

        for dot_index, dot in enumerate(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            px3, py3, pz3 = self.pointOnEdgeKey(edge_key, dot["t"])
            rx, ry, rz = self.rotatePoint(px3, py3, pz3)
            px, py = self.projectPoint(rx, ry, rz)

            dot_color, label_color, alpha = self.intersectionColors(edge_key, selected_face_edge_keys)
            self.drawIntersectionPoint(dot_index, px, py, dot["t"], dot_color, label_color, alpha)

    def drawSectionPolygonBetweenPoints(self):
        if len(self.intersections) <= 1:
            return

        if self.isNetViewActive():
            if self.isFaceOrEdgeMode() and self.selected_face is not None:
                face_indices = [self.selected_face]
            else:
                face_indices = range(len(self.faces))

            for face_index in face_indices:
                face_points = []
                for dot in self.intersections:
                    edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
                    edge_index = self.netEdgeIndexForKeyOnFace(face_index, edge_key)
                    if edge_index is None:
                        continue
                    local_t = self.canonicalTToNetFaceEdgeT(face_index, edge_index, float(dot["t"]))
                    p0, p1 = self.netFaceEdgeEndpointPoints(face_index, edge_index)
                    face_points.append(self.interpolatePointOnScreenSegment(p0, p1, local_t))

                unique_points = []
                for point in face_points:
                    if not any((point[0] - old[0]) ** 2 + (point[1] - old[1]) ** 2 <= 4.0 for old in unique_points):
                        unique_points.append(point)

                if len(unique_points) < 2:
                    continue

                if len(unique_points) == 2:
                    a, b = unique_points
                else:
                    best_pair = (unique_points[0], unique_points[1])
                    best_dist = -1.0
                    for i in range(len(unique_points)):
                        for j in range(i + 1, len(unique_points)):
                            dist = (unique_points[i][0] - unique_points[j][0]) ** 2 + (unique_points[i][1] - unique_points[j][1]) ** 2
                            if dist > best_dist:
                                best_dist = dist
                                best_pair = (unique_points[i], unique_points[j])
                    a, b = best_pair

                Color(1, 0, 0, 1)
                Line(points=[a[0], a[1], b[0], b[1]], width=1.2)
            return

        screen_points = []
        for dot in self.intersections:
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            screen_points.append(self.projectPointOnEdge(edge_key, dot["t"]))

        center_x = sum(point[0] for point in screen_points) / len(screen_points)
        center_y = sum(point[1] for point in screen_points) / len(screen_points)
        screen_points.sort(key=lambda screen_point: atan2(screen_point[1] - center_y, screen_point[0] - center_x))

        vertices = []
        for x, y in screen_points:
            vertices.extend([x, y, 0.0, 0.0])

        indices = list(range(len(screen_points)))
        flat_points = [coord for point in screen_points for coord in point]

        Color(1, 0, 0, 0.25)
        Mesh(vertices=vertices, indices=indices, mode="triangle_fan")
        Color(1, 0, 0, 1)
        Line(points=flat_points, width=1.2, close=True)

    def drawActiveEdgeEditor(self):
        if not (self.isEdgeMode() and self.current_edge_key is not None):
            return

        (p0x, p0y), (p1x, p1y) = self.projectEdgeEndpointPoints(self.current_edge_key)
        label_0 = (p0x, (p0y + p1y) / 2 - DOT_LABEL_OFFSET)
        label_1 = (p1x, (p0y + p1y) / 2 - DOT_LABEL_OFFSET)

        if self.isNetViewActive() and self.selected_face is not None:
            polygon = self.face_polygons[int(self.selected_face)]
            center_x = sum(point[0] for point in polygon) / len(polygon)
            center_y = sum(point[1] for point in polygon) / len(polygon)
            mid_x = 0.5 * (p0x + p1x)
            mid_y = 0.5 * (p0y + p1y)
            out_x = mid_x - center_x
            out_y = mid_y - center_y
            out_len = sqrt(out_x * out_x + out_y * out_y)
            if out_len > 1e-8:
                label_offset = dp(14)
                out_x = out_x / out_len * label_offset
                out_y = out_y / out_len * label_offset
                label_0 = (p0x + out_x, p0y + out_y)
                label_1 = (p1x + out_x, p1y + out_y)

        Color(1, 1, 0, 1)
        self.drawLabel("0", label_0[0], label_0[1], font_size=sp(14), color=(1, 1, 0, 1))
        self.drawLabel("1", label_1[0], label_1[1], font_size=sp(14), color=(1, 1, 0, 1))

        display_t = self.current_t
        if self.isNetViewActive() and self.selected_face is not None:
            edge_index = self.edgeIndexForKeyOnSelectedFace(self.current_edge_key)
            if edge_index is not None:
                p0, p1 = self.netFaceEdgeEndpointPoints(self.selected_face, edge_index)
                pdx, pdy = self.interpolatePointOnScreenSegment(p0, p1, display_t)
            else:
                pdx, pdy = self.projectPointOnEdge(self.current_edge_key, self.current_t)
        else:
            pdx, pdy = self.projectPointOnEdge(self.current_edge_key, self.current_t)

        Color(0, 1, 0, 1)
        Ellipse(
            pos=(pdx - ACTIVE_DOT_RADIUS, pdy - ACTIVE_DOT_RADIUS),
            size=(2 * ACTIVE_DOT_RADIUS, 2 * ACTIVE_DOT_RADIUS),
        )

        Color(1, 1, 0, 1)
        self.drawLabel(
            f"{display_t:.2f}",
            pdx,
            pdy + DOT_LABEL_OFFSET,
            font_size=sp(13),
            color=(1, 1, 0, 1),
        )

    def projectModelPoint(self, point) -> tuple[float, float]:
        rx, ry, rz = self.rotatePoint(float(point[0]), float(point[1]), float(point[2]))
        return self.projectPoint(rx, ry, rz)

    def drawLine3d(self, a, b, color=(1, 1, 1, 1), width=1.5):
        ax, ay = self.projectModelPoint(a)
        bx, by = self.projectModelPoint(b)
        Color(*color)
        Line(points=[ax, ay, bx, by], width=width)

    def computeSplitCutEntriesForSide(self, center, normal, offset_vec):
        eps = 1e-7
        entries = []
        for v0, v1 in self.edges:
            a = self.vertexVec(v0)
            b = self.vertexVec(v1)
            da = float(np.dot(a - center, normal))
            db = float(np.dot(b - center, normal))

            candidates = []
            if abs(da) <= eps:
                candidates.append((a, 0.0))
            if abs(db) <= eps:
                candidates.append((b, 1.0))
            if da * db < -eps:
                t = da / (da - db)
                candidates.append((a + (b - a) * t, float(t)))

            for point, t in candidates:
                entry = {
                    "edge_key": self.canonicalEdgeKey(v0, v1),
                    "t": self.clamp01(t),
                    "point": point + offset_vec,
                }
                if not any(np.linalg.norm(entry["point"] - old["point"]) < 1e-6 for old in entries):
                    entries.append(entry)

        if len(entries) >= 3:
            poly_center = np.mean([entry["point"] for entry in entries], axis=0)
            self.sortPlanarEntries(entries, poly_center, normal)
        return entries

    def drawSplitCapFace(self, cut_entries):
        polygon3d = [entry["point"] for entry in cut_entries]
        screen_points = [self.projectModelPoint(point) for point in polygon3d]

        if len(screen_points) >= 3:
            vertices = []
            for x, y in screen_points:
                vertices.extend([x, y, 0.0, 0.0])
            indices = []
            for index in range(1, len(screen_points) - 1):
                indices.extend([0, index, index + 1])
            flat = [coord for point in screen_points for coord in point]

            Color(1.0, 0.0, 0.0, 0.25)
            Mesh(vertices=vertices, indices=indices, mode="triangles")
            Color(1.0, 0.0, 0.0, 1.0)
            Line(points=flat, width=1.4, close=True)

        for cut_index, entry in enumerate(cut_entries):
            x, y = self.projectModelPoint(entry["point"])
            Color(1.0, 0.0, 0.0, 1.0)
            Ellipse(pos=(x - DOT_RADIUS, y - DOT_RADIUS), size=(2 * DOT_RADIUS, 2 * DOT_RADIUS))
            if self.show_coord_labels:
                self.drawLabel(
                    self.pointLabelText(cut_index, entry["t"]),
                    x + DOT_LABEL_OFFSET,
                    y + DOT_LABEL_OFFSET,
                    font_size=sp(13),
                    color=(1, 1, 0, 1),
                )

    def drawSplitCube(self):
        geom, msg = self.buildSectionGeometry()
        if geom is None:
            self.drawEdges()
            self.drawIntersections()
            if msg:
                self.drawLabel(msg, self.center_x, self.y + BOTTOM_T_LABEL_Y, font_size=sp(14), color=(1, 1, 1, 1))
            return

        center = geom["center"]
        normal = geom["normal"]
        sep = 0.36
        eps = 1e-7
        cut_faces = []

        for side in (1.0, -1.0):
            offset_vec = normal * sep * side
            for v0, v1 in self.edges:
                a = self.vertexVec(v0)
                b = self.vertexVec(v1)
                da = float(np.dot(a - center, normal))
                db = float(np.dot(b - center, normal))
                a_on_side = da >= -eps if side > 0 else da <= eps
                b_on_side = db >= -eps if side > 0 else db <= eps
                if a_on_side and b_on_side:
                    self.drawLine3d(a + offset_vec, b + offset_vec, color=(1, 1, 1, 1), width=1.5)
                elif da * db < -eps:
                    t = da / (da - db)
                    cut = a + (b - a) * t
                    if a_on_side:
                        self.drawLine3d(a + offset_vec, cut + offset_vec, color=(1, 1, 1, 1), width=1.5)
                    elif b_on_side:
                        self.drawLine3d(b + offset_vec, cut + offset_vec, color=(1, 1, 1, 1), width=1.5)

            cap_entries = self.computeSplitCutEntriesForSide(center, normal, offset_vec)
            depth = 0.0
            for entry in cap_entries:
                point = entry["point"]
                _, _, z = self.rotatePoint(float(point[0]), float(point[1]), float(point[2]))
                depth += z
            depth /= max(1, len(cap_entries))
            cut_faces.append((depth, cap_entries))

        cut_faces.sort(key=lambda cut_face: cut_face[0], reverse=True)
        for _, cap_entries in cut_faces:
            self.drawSplitCapFace(cap_entries)

    def buildSplitCapPayload(self):
        geom, _msg = self.buildSectionGeometry()
        if geom is None:
            return []
        center = geom["center"]
        normal = geom["normal"]
        payload = []
        for side in (1.0, -1.0):
            offset_vec = normal * 0.36 * side
            cap_entries = self.computeSplitCutEntriesForSide(center, normal, offset_vec)
            payload.append({
                "side": side,
                "points": [
                    {
                        "edge_key": list(entry["edge_key"]),
                        "t": float(entry["t"]),
                        "label": self.pointLetter(index),
                        "point": [float(entry["point"][0]), float(entry["point"][1]), float(entry["point"][2])],
                    }
                    for index, entry in enumerate(cap_entries)
                ],
            })
        return payload

    def drawScanPointSuggestions(self):
        suggestions = self.scanPointSuggestionsForSelectedFace()
        if not suggestions:
            return

        for suggestion in suggestions:
            x = float(suggestion["x"])
            y = float(suggestion["y"])
            radius = ACTIVE_DOT_RADIUS * 1.25

            Color(0, 0, 0, 1)
            Ellipse(pos=(x - radius, y - radius), size=(2 * radius, 2 * radius))
            Color(1, 0, 0, 1)
            Line(circle=(x, y, radius), width=dp(1.7))

            plus = radius * 0.55
            Line(points=[x - plus, y, x + plus, y], width=dp(1.2))
            Line(points=[x, y - plus, x, y + plus], width=dp(1.2))

            if self.show_coord_labels:
                self.drawLabel(
                    f"{float(suggestion['local_t']):.2f}",
                    x + DOT_LABEL_OFFSET,
                    y - DOT_LABEL_OFFSET,
                    font_size=sp(12),
                    color=(1, 0, 0, 1),
                )

    def calculateScanSectionPreviewBox(self) -> tuple[float, float, float, float, float]:
        box_w = min(dp(138), max(dp(96), self.width * 0.30))
        box_h = box_w
        margin = dp(10)
        x0 = self.x + margin
        y0 = self.y + self.height - margin - box_h
        return x0, y0, box_w, box_h, margin

    def drawScanSectionPreview(self):
        if not self.isNetViewActive():
            return

        x0, y0, box_w, box_h, _margin = self.calculateScanSectionPreviewBox()

        Color(0, 0, 0, 0.72)
        Rectangle(pos=(x0, y0), size=(box_w, box_h))
        Color(1, 1, 1, 0.65)
        Line(rectangle=(x0, y0, box_w, box_h), width=1.0)
        self.drawLabel("SECTION", x0 + box_w / 2.0, y0 + box_h - dp(13), font_size=sp(11), color=(1, 1, 1, 1))

        geom, _msg = self.buildSectionGeometry()
        if geom is None:
            self.drawLabel("ADJUST DOTS", x0 + box_w / 2.0, y0 + box_h / 2.0, font_size=sp(10), color=(1, 0.25, 0.25, 1))
            return

        points = [np.array(point, dtype=float) for point in geom.get("points", [])]
        if len(points) < 2:
            return

        center = np.array(geom["center"], dtype=float)
        normal = np.array(geom["normal"], dtype=float)
        u, v = self.planeSortBasis(points, center, normal)

        coords = [
            (float(np.dot(point - center, u)), float(np.dot(point - center, v)))
            for point in points
        ]
        min_x = min(x for x, _ in coords)
        max_x = max(x for x, _ in coords)
        min_y = min(y for _, y in coords)
        max_y = max(y for _, y in coords)
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        pad = dp(24)
        scale = min((box_w - 2.0 * pad) / span_x, (box_h - 2.0 * pad) / span_y)
        scale = max(1.0, scale)

        screen_points = []
        for px, py in coords:
            sx = x0 + box_w / 2.0 + px * scale
            sy = y0 + (box_h - dp(12)) / 2.0 + py * scale
            screen_points.append((sx, sy))

        if len(screen_points) >= 3:
            vertices = []
            for sx, sy in screen_points:
                vertices.extend([sx, sy, 0.0, 0.0])
            Color(1, 0, 0, 0.24)
            Mesh(vertices=vertices, indices=list(range(len(screen_points))), mode="triangle_fan")
            Color(1, 0, 0, 1)
            Line(points=[coord for point in screen_points for coord in point], width=1.2, close=True)
        else:
            Color(1, 0, 0, 1)
            Line(points=[coord for point in screen_points for coord in point], width=1.2)

        Color(1, 0, 0, 1)
        for sx, sy in screen_points:
            radius = dp(2.6)
            Ellipse(pos=(sx - radius, sy - radius), size=(2 * radius, 2 * radius))

    def drawSectionValidationWarning(self):
        if len(self.intersections) < 3 or self.split_mode:
            return
        ok, msg = self.validateSplitDefinition()
        if ok or not msg:
            return
        self.drawWarningText(self.validationMessageForUser(msg), alpha=0.95)

    def drawScene(self):
        self.updateGeometry()
        self.drawBackground()

        if self.split_mode:
            self.drawSplitCube()
            self.drawInvalidPlacementFlash()
            return

        self.drawEdges()
        self.drawFaceNumbers()
        self.drawEdgeNumbers()
        self.drawIntersections()
        self.drawSectionPolygonBetweenPoints()
        self.drawScanPointSuggestions()
        self.drawActiveEdgeEditor()
        self.drawSectionValidationWarning()
        self.drawScanSectionPreview()
        self.drawInvalidPlacementFlash()

    def updateCanvas(self):
        self.canvas.clear()
        with self.canvas:
            self.drawScene()
