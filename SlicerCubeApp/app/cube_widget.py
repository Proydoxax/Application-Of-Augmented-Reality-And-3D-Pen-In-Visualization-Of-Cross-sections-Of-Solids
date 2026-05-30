import math
from math import sqrt

import numpy as np
from kivy.uix.widget import Widget
from kivy.clock import Clock

from .geometry import pointInConvexPolygon, distancePointToSegment
from .constants import (
    ANGLE_EPSILON,
    CUBE_CAMERA_DISTANCE,
    CUBE_EDGES,
    CUBE_FACES,
    CUBE_VERTICES,
    CUBE_VERTEX_VECTORS,
    DRAG_THRESHOLD,
    DISTANCE_EPSILON,
    DOT_PICK_THRESHOLD,
    EDGE_PICK_EXTEND,
    EDGE_PICK_THRESHOLD,
    FACE_CAMERA_DISTANCE,
    FACE_CENTERS,
    FACE_DOWN_VECTORS,
    FACE_NORMALS,
    IGNORED_TOUCH_BUTTONS,
    PROJECTION_SCALE,
    canonicalEdgeKey as cubeCanonicalEdgeKey,
    clamp01,
    edgeKeyFromFaceEdge as cubeEdgeKeyFromFaceEdge,
    parseFaceEdgeRows,
    pointOnEdgeKey as cubePointOnEdgeKey,
)
from .cube_widget_net import CubeNetMixin
from .cube_widget_rendering import CubeRenderMixin
from .cube_widget_rotation import CubeRotationMixin
from .cube_widget_section import CubeSectionMixin


class CubeWidget(CubeSectionMixin, CubeNetMixin, CubeRotationMixin, CubeRenderMixin, Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.vertices = CUBE_VERTICES
        self.edges = CUBE_EDGES
        self.faces = CUBE_FACES
        self.face_normals = FACE_NORMALS
        self.face_down_vectors = FACE_DOWN_VECTORS
        self.label_texture_cache = {}

        self.cube_pitch = 20.0
        self.cube_yaw = 30.0

        self.saved_cube_pitch = self.cube_pitch
        self.saved_cube_yaw = self.cube_yaw

        self.camera_distance = CUBE_CAMERA_DISTANCE
        self.target_camera_distance = CUBE_CAMERA_DISTANCE

        self.touch_start_pos = None
        self.dragging = False
        self.drag_threshold = DRAG_THRESHOLD

        self.show_face_numbers = True
        self.show_coord_labels = True
        self.show_edge_numbers = False

        self.net_2d_mode = False
        self.scan_verification_mode = False
        self.scan_suggestion_hit_radius = DOT_PICK_THRESHOLD * 2.4
        self.scan_direct_edge_hit_radius = EDGE_PICK_THRESHOLD * 1.35
        self.scan_drag_dot_index = None
        self.scan_drag_started = False

        self.intersections: list[dict] = []
        self.split_mode = False
        self.invalid_flash_text = ""
        self.invalid_flash_alpha = 0.0
        self.invalid_flash_event = None

        self.point_erase_mode = False
        self.erase_candidate_index = None
        self.erase_candidate_indices = set()
        self.erase_hit_radius = DOT_PICK_THRESHOLD * 2.4
        self.split_saved_camera_distance = None
        self.split_zoom_distance = FACE_CAMERA_DISTANCE

        self.mode = "cube"
        self.selected_face = None
        self.current_edge_key = None
        self.current_t = 0.5
        self.edit_dot_index = None

        self.proj_vertices = []
        self.rot_vertices = []
        self.face_polygons = []
        self.face_depths = []
        self.front_face = None

        self.face_edge_pseudo = {}

        self.camera_animation_blend = 0.10

        initial_rotation = self.cubeRotationMatrix(self.cube_pitch, self.cube_yaw)
        self.current_quat = self.quatFromMatrix(initial_rotation)
        self.target_quat = self.current_quat.copy()
        self.current_rotation = initial_rotation.copy()

        self.face_view_rotation = initial_rotation.copy()

        Clock.schedule_interval(self.animateCamera, 1 / 60.0)
        self.bind(size=lambda *_: self.updateCanvas())
        self.bind(pos=lambda *_: self.updateCanvas())

        self.updateCanvas()

    def callParentHandler(self, method_name, *args):
        parent = self.parent
        if parent and hasattr(parent, method_name):
            method = getattr(parent, method_name)
            try:
                method(*args)
            except TypeError:
                if args:
                    method(*args[:-1])
                else:
                    raise

    def isCubeMode(self):
        return self.mode == "cube"

    def isEdgeMode(self):
        return self.mode == "edge"

    def isFaceOrEdgeMode(self):
        return self.mode in ("face", "edge")

    def isPointEraseMode(self):
        return bool(getattr(self, "point_erase_mode", False))

    def clearEdgeEditState(self):
        self.current_edge_key = None
        self.current_t = 0.5
        self.edit_dot_index = None

    def resetCubeEditState(self):
        self.mode = "cube"
        self.selected_face = None
        self.clearEdgeEditState()

    def resetScanDragState(self):
        self.scan_drag_dot_index = None
        self.scan_drag_started = False

    @staticmethod
    def canonicalEdgeKey(v_a, v_b):
        return cubeCanonicalEdgeKey(v_a, v_b)

    @staticmethod
    def edgeKeyFromFaceEdge(face_index, edge_index):
        return cubeEdgeKeyFromFaceEdge(face_index, edge_index)

    @staticmethod
    def pointOnEdgeKey(edge_key, t):
        return cubePointOnEdgeKey(edge_key, t)

    @staticmethod
    def clamp01(value):
        return clamp01(value)

    @staticmethod
    def vertexVec(index):
        return CUBE_VERTEX_VECTORS[index]

    def currentEdgeTFromTouchPosition(self, pos):
        if self.current_edge_key is None:
            return self.current_t

        (ax, ay), (bx, by) = self.projectEdgeEndpointPoints(self.current_edge_key)
        px, py = pos
        vx = bx - ax
        vy = by - ay
        denominator = vx * vx + vy * vy
        if denominator <= 1e-8:
            return self.current_t
        t = ((px - ax) * vx + (py - ay) * vy) / denominator
        return self.clamp01(t)

    def on_touch_down(self, touch):
        if hasattr(touch, "button") and touch.button in IGNORED_TOUCH_BUTTONS:
            return False

        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.touch_start_pos = touch.pos
        self.dragging = False
        self.resetScanDragState()
        if self.isScanDirectEditActive():
            dot_index = self.pickPointAnywhere(pos=touch.pos, radius=DOT_PICK_THRESHOLD * 1.6)
            if dot_index is not None:
                self.scan_drag_dot_index = dot_index
        return True

    def on_touch_move(self, touch):
        if hasattr(touch, "button") and touch.button in IGNORED_TOUCH_BUTTONS:
            return True

        if self.touch_start_pos is None:
            return super().on_touch_move(touch)

        x, y = touch.pos
        start_x, start_y = self.touch_start_pos
        dx = x - start_x
        dy = y - start_y

        if not self.dragging:
            if abs(dx) > self.drag_threshold or abs(dy) > self.drag_threshold:
                self.dragging = True

        if self.dragging and self.scan_drag_dot_index is not None and self.isScanDirectEditActive():
            if self.moveScanPointToTouch(self.scan_drag_dot_index, touch.pos):
                self.scan_drag_started = True
            self.touch_start_pos = touch.pos
            return True

        if self.dragging and self.isEdgeMode() and self.current_edge_key is not None:
            self.setCurrentEdgeT(self.currentEdgeTFromTouchPosition(touch.pos))
            self.callParentHandler("onEdgeEditorTChanged", self.current_t)
            self.touch_start_pos = touch.pos
            return True

        if self.dragging and self.isCubeMode() and self.isNetViewActive():
            return True

        if self.dragging and self.isCubeMode():
            yaw_delta = -dx * 0.5
            normalized_pitch = self.cube_pitch % 360.0
            if 90.0 < normalized_pitch < 270.0:
                yaw_delta = -yaw_delta

            self.cube_yaw = self.normalizeAngle(self.cube_yaw + yaw_delta)
            self.cube_pitch = self.normalizeAngle(self.cube_pitch + dy * 0.5)

            cube_rotation = self.cubeRotationMatrix(self.cube_pitch, self.cube_yaw)
            q_cube = self.quatFromMatrix(cube_rotation)

            self.current_quat = q_cube.copy()
            self.target_quat = q_cube.copy()
            self.current_rotation = cube_rotation.copy()

            self.touch_start_pos = touch.pos
            self.updateCanvas()

        return True

    def on_touch_up(self, touch):
        if hasattr(touch, "button") and touch.button in IGNORED_TOUCH_BUTTONS:
            return True

        if self.touch_start_pos is None:
            return super().on_touch_up(touch)

        scan_dot_pressed = self.scan_drag_dot_index is not None
        scan_dot_moved = bool(getattr(self, "scan_drag_started", False))

        if scan_dot_moved:
            self.callParentHandler("onScanSuggestionAdded")
        elif not self.dragging and not scan_dot_pressed:
            self.handleClick(touch.pos)

        self.touch_start_pos = None
        self.dragging = False
        self.resetScanDragState()
        return True

    def animateCamera(self, _dt):
        changed = False

        current_distance = self.camera_distance
        target_distance = self.target_camera_distance

        if abs(current_distance - target_distance) >= DISTANCE_EPSILON:
            self.camera_distance += (target_distance - current_distance) * self.camera_animation_blend
            changed = True
        elif self.camera_distance != target_distance:
            self.camera_distance = target_distance
            changed = True

        angular_diff = self.quatAngleTo(self.current_quat, self.target_quat)

        if angular_diff >= ANGLE_EPSILON * math.pi / 180.0:
            q = self.quatSphericalInterpolate(self.current_quat, self.target_quat, self.camera_animation_blend)
            self.setCurrentQuat(q)
            changed = True
        else:
            target_q = self.quatNormalize(self.target_quat)
            if not np.allclose(self.current_quat, target_q, atol=1e-6):
                self.setCurrentQuat(target_q)
                changed = True

        if changed:
            self.updateCanvas()

    def rotatePoint(self, x, y, z):
        rx, ry, rz = self.current_rotation @ np.array([x, y, z], dtype=float)
        return float(rx), float(ry), float(rz)

    def projectPointWithDistance(self, x, y, z, camera_distance):
        z_shifted = z + camera_distance
        if z_shifted <= ANGLE_EPSILON:
            z_shifted = ANGLE_EPSILON

        base = min(self.width, self.height) * PROJECTION_SCALE
        if base <= 0:
            base = 200.0

        factor = base / z_shifted
        x_proj = x * factor + self.center_x
        y_proj = y * factor + self.center_y
        return x_proj, y_proj

    def projectPoint(self, x, y, z):
        return self.projectPointWithDistance(x, y, z, self.camera_distance)

    def updateGeometry(self):
        if self.isNetViewActive():
            self.proj_vertices = []
            self.rot_vertices = []
            self.face_polygons = [self.netFacePolygonPoints(face_index) for face_index in range(len(self.faces))]
            self.face_depths = [0.0 for _ in self.faces]
            self.front_face = None
            return

        self.proj_vertices = []
        self.rot_vertices = []

        for vx, vy, vz in self.vertices:
            rx, ry, rz = self.rotatePoint(vx, vy, vz)
            px, py = self.projectPoint(rx, ry, rz)
            self.rot_vertices.append((rx, ry, rz))
            self.proj_vertices.append((px, py))

        self.face_polygons = []
        self.face_depths = []

        for face_vertices in self.faces:
            polygon = [self.proj_vertices[idx] for idx in face_vertices]
            mean_z = sum(self.rot_vertices[idx][2] for idx in face_vertices) / len(face_vertices)
            self.face_polygons.append(polygon)
            self.face_depths.append(mean_z)

        if self.face_depths:
            self.front_face = min(range(len(self.face_depths)), key=lambda i: self.face_depths[i])
        else:
            self.front_face = None

    @staticmethod
    def faceCenter(face_index):
        return FACE_CENTERS[face_index]

    def parseIntersectionsFromString(self, data: str):
        parsed_dots = []

        for face, edge, t in parseFaceEdgeRows(data, face_count=len(self.faces)):
            edge_key = self.netEdgeKeyFromFaceEdge(face, edge)
            canonical_t = self.netFaceEdgeTToCanonicalT(face, edge, t)
            parsed_dots.append({
                "v0": edge_key[0],
                "v1": edge_key[1],
                "t": canonical_t,
                "source_face": face,
                "source_edge": edge,
            })

        return self.dedupeIntersectionsByGeometricPoint(parsed_dots)

    def setIntersectionsFromString(self, data: str):
        self.intersections = self.parseIntersectionsFromString(data)
        if self.split_mode:
            self.exitSplitZoom()
        self.split_mode = False
        self.updateCanvas()

    def pickFace(self, pos):
        self.updateGeometry()
        x, y = pos

        best_face = None
        best_depth = None

        for face_index, polygon in enumerate(self.face_polygons):
            if pointInConvexPolygon((x, y), polygon):
                depth = self.face_depths[face_index]
                if best_face is None or depth < best_depth:
                    best_face = face_index
                    best_depth = depth

        return best_face

    def pickEdgeOnSelectedFace(self, pos):
        if self.selected_face is None:
            return None

        x, y = pos
        face_vertices = self.faces[self.selected_face]

        best_edge = None
        best_distance = None

        for edge_index in range(4):
            if self.isNetViewActive():
                (x1, y1), (x2, y2) = self.netFaceEdgeEndpointPoints(self.selected_face, edge_index)
            else:
                i0 = face_vertices[edge_index % 4]
                i1 = face_vertices[(edge_index + 1) % 4]

                x1, y1 = self.proj_vertices[i0]
                x2, y2 = self.proj_vertices[i1]

            dx = x2 - x1
            dy = y2 - y1
            length = sqrt(dx * dx + dy * dy) or 1.0

            extend_x = dx / length
            extend_y = dy / length

            ax = x1 - extend_x * EDGE_PICK_EXTEND
            ay = y1 - extend_y * EDGE_PICK_EXTEND
            bx = x2 + extend_x * EDGE_PICK_EXTEND
            by = y2 + extend_y * EDGE_PICK_EXTEND

            dist = distancePointToSegment(x, y, ax, ay, bx, by)
            if dist <= EDGE_PICK_THRESHOLD:
                if best_edge is None or dist < best_distance:
                    best_edge = edge_index
                    best_distance = dist

        return best_edge

    def pickPointOnSelectedFace(self, pos):
        if self.selected_face is None:
            return None

        self.updateGeometry()
        x, y = pos
        best_dot_index = None
        best_distance = None

        face_edge_keys = self.selectedFaceEdgeKeys()

        for dot_index, dot in enumerate(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            if edge_key not in face_edge_keys:
                continue

            px, py = self.projectPointOnEdge(edge_key, dot["t"])
            dist = sqrt((x - px) ** 2 + (y - py) ** 2)
            if dist <= DOT_PICK_THRESHOLD:
                if best_dot_index is None or dist < best_distance:
                    best_dot_index = dot_index
                    best_distance = dist

        return best_dot_index

    def pickPointAnywhere(self, pos, radius=None):
        self.updateGeometry()
        if radius is None:
            radius = DOT_PICK_THRESHOLD
        x, y = pos
        best_dot_index = None
        best_distance = None
        face_context = self.isFaceOrEdgeMode() and self.selected_face is not None
        for dot_index, dot in enumerate(self.intersections):
            edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])
            if self.isNetViewActive():
                positions = self.netPointScreenPositions(
                    dot,
                    prefer_face_index=self.selected_face if face_context else None,
                    include_all=face_context,
                )
                point_iter = [(px, py) for _face, _edge, px, py, _local_t in positions]
            else:
                point_iter = [self.projectPointOnEdge(edge_key, dot["t"])]
            for px, py in point_iter:
                dist = sqrt((x - px) ** 2 + (y - py) ** 2)
                if dist <= radius:
                    if best_dot_index is None or dist < best_distance:
                        best_dot_index = dot_index
                        best_distance = dist
        return best_dot_index

    def handleClick(self, pos):
        self.updateGeometry()

        if self.isPointEraseMode():
            dot_index = self.pickPointAnywhere(pos, radius=self.erase_hit_radius)
            if dot_index is not None:
                selected = set(getattr(self, "erase_candidate_indices", set()) or set())
                if dot_index in selected:
                    selected.remove(dot_index)
                else:
                    selected.add(dot_index)
                self.erase_candidate_indices = selected
                self.syncEraseSelectionState()
                self.updateCanvas()
                self.callParentHandler("onPointEraseSelectionChanged")
            return

        if self.split_mode:
            return

        if self.isCubeMode():
            face_index = self.pickFace(pos)
            if face_index is not None:
                self.callParentHandler("enterFaceView", face_index)
            return

        if self.selected_face is None:
            return

        selected_polygon = self.face_polygons[self.selected_face]
        inside_face = pointInConvexPolygon(pos, selected_polygon)

        if self.isScanDirectEditActive():
            suggestion = self.pickScanPointSuggestion(pos)
            if suggestion is not None:
                if self.addSuggestedScanPoint(suggestion):
                    self.callParentHandler("onScanSuggestionAdded")
                return

            if self.pickPointAnywhere(pos, radius=DOT_PICK_THRESHOLD * 1.6) is not None:
                return

            if self.addScanPointAtTouch(pos):
                self.callParentHandler("onScanSuggestionAdded")
                return
            if not inside_face:
                self.callParentHandler("cancelEdit")
            return

        if self.isEdgeMode():
            edge_index = self.pickEdgeOnSelectedFace(pos)
            active_edge_index = self.edgeIndexForKeyOnSelectedFace(self.current_edge_key) if self.current_edge_key is not None else None
            if edge_index is not None and (active_edge_index is None or edge_index == active_edge_index):
                self.setCurrentEdgeT(self.currentEdgeTFromTouchPosition(pos))
                self.callParentHandler("onEdgeEditorTChanged", self.current_t)
                return
            self.callParentHandler("cancelEdit")
            return

        dot_index = self.pickPointOnSelectedFace(pos) if inside_face else None
        if dot_index is not None:
            self.callParentHandler("enterEdgeEditForPoint", dot_index)
            return

        edge_index = self.pickEdgeOnSelectedFace(pos)
        if edge_index is not None:
            self.callParentHandler("enterEdgeEdit", edge_index, pos)
            return

        if not inside_face:
            self.callParentHandler("cancelEdit")
            return

    def projectVerticesForRotation(self, rotation_matrix, camera_distance):
        proj_vertices = []
        for vx, vy, vz in self.vertices:
            rx, ry, rz = rotation_matrix @ np.array([vx, vy, vz], dtype=float)
            px, py = self.projectPointWithDistance(float(rx), float(ry), float(rz), camera_distance)
            proj_vertices.append((px, py))
        return proj_vertices

    def computeEdgePseudoIndices(self, face_index, rotation_matrix):
        proj_vertices = self.projectVerticesForRotation(rotation_matrix, FACE_CAMERA_DISTANCE)

        face_vertices = self.faces[face_index]
        midpoints = []

        for edge_index in range(4):
            i0 = face_vertices[edge_index % 4]
            i1 = face_vertices[(edge_index + 1) % 4]
            x1, y1 = proj_vertices[i0]
            x2, y2 = proj_vertices[i1]
            midpoints.append((0.5 * (x1 + x2), 0.5 * (y1 + y2)))

        xs = [midpoint[0] for midpoint in midpoints]
        ys = [midpoint[1] for midpoint in midpoints]

        bottom_idx = max(range(4), key=lambda i: ys[i])
        top_idx = min(range(4), key=lambda i: ys[i])
        left_idx = min(range(4), key=lambda i: xs[i])
        right_idx = max(range(4), key=lambda i: xs[i])

        self.face_edge_pseudo[face_index] = {
            bottom_idx: 0,
            right_idx: 1,
            top_idx: 2,
            left_idx: 3,
        }

    @staticmethod
    def rollForPseudoIndex(pseudo_index):
        if pseudo_index == 0:
            return 180.0
        if pseudo_index == 1:
            return 90.0
        if pseudo_index == 2:
            return 0.0
        if pseudo_index == 3:
            return -90.0
        return 0.0

    def edgeIndexForKeyOnSelectedFace(self, edge_key):
        if self.selected_face is None:
            return None

        if self.isNetViewActive():
            return self.netEdgeIndexForKeyOnFace(self.selected_face, edge_key)

        for edge_index in range(4):
            if self.edgeKeyFromFaceEdge(self.selected_face, edge_index) == edge_key:
                return edge_index

        return None

    def enterFaceViewMode(self, face_index):
        if self.isNetViewActive():
            self.mode = "face"
            self.selected_face = face_index
            self.clearEdgeEditState()
            self.updateCanvas()
            return

        self.saved_cube_pitch = self.cube_pitch
        self.saved_cube_yaw = self.cube_yaw

        self.mode = "face"
        self.selected_face = face_index
        self.clearEdgeEditState()

        face_rotation = self.makeFaceViewRotationFromCurrent(face_index)
        self.face_view_rotation = face_rotation.copy()

        self.setTargetRotation(face_rotation)
        self.target_camera_distance = FACE_CAMERA_DISTANCE

        self.computeEdgePseudoIndices(face_index, face_rotation)
        self.updateCanvas()

    def enterEdgeEditModeNew(self, edge_index, touch_pos=None):
        if self.selected_face is None:
            return

        self.mode = "edge"
        if self.isNetViewActive():
            self.current_edge_key = self.netEdgeKeyFromFaceEdge(self.selected_face, edge_index)
        else:
            self.current_edge_key = self.edgeKeyFromFaceEdge(self.selected_face, edge_index)
        self.current_t = 0.5
        if touch_pos is not None:
            self.current_t = self.currentEdgeTFromTouchPosition(touch_pos)
        self.edit_dot_index = None

        if not self.isNetViewActive():
            self.setEdgeViewTarget(edge_index)
        self.updateCanvas()

    def enterEdgeEditModeExisting(self, dot_index):
        if not (0 <= dot_index < len(self.intersections)):
            return

        dot = self.intersections[dot_index]
        edge_key = self.canonicalEdgeKey(dot["v0"], dot["v1"])

        self.mode = "edge"
        self.current_edge_key = edge_key
        edge_index = self.edgeIndexForKeyOnSelectedFace(edge_key)
        if self.isNetViewActive() and self.selected_face is not None and edge_index is not None:
            self.current_t = self.canonicalTToNetFaceEdgeT(self.selected_face, edge_index, dot["t"])
        else:
            self.current_t = dot["t"]
        self.edit_dot_index = dot_index

        if not self.isNetViewActive():
            if edge_index is None:
                self.restoreFaceViewTarget()
            else:
                self.setEdgeViewTarget(edge_index)

        self.updateCanvas()

    def exitToCube(self):
        self.resetCubeEditState()

        if not self.isNetViewActive():
            self.cube_pitch = self.saved_cube_pitch
            self.cube_yaw = self.saved_cube_yaw

            cube_rotation = self.cubeRotationMatrix(self.cube_pitch, self.cube_yaw)
            self.setTargetRotation(cube_rotation)
            self.target_camera_distance = CUBE_CAMERA_DISTANCE

        self.updateCanvas()

    def cancelEdgeEdit(self):
        self.mode = "face"
        self.clearEdgeEditState()

        if not self.isNetViewActive():
            self.restoreFaceViewTarget()
        self.updateCanvas()

    def confirmEdgePoint(self):
        if self.current_edge_key is None:
            self.exitToCube()
            return False

        v0, v1 = self.current_edge_key
        editor_t = self.clamp01(self.current_t)
        source_edge = self.edgeIndexForKeyOnSelectedFace(self.current_edge_key)
        if self.isNetViewActive() and self.selected_face is not None and source_edge is not None:
            t = self.netFaceEdgeTToCanonicalT(self.selected_face, source_edge, editor_t)
        else:
            t = editor_t
        candidate = [dict(dot) for dot in self.intersections]
        new_dot = {"v0": v0, "v1": v1, "t": t}
        if self.selected_face is not None and source_edge is not None:
            new_dot["source_face"] = int(self.selected_face)
            new_dot["source_edge"] = int(source_edge)
        if self.edit_dot_index is not None and 0 <= self.edit_dot_index < len(candidate):
            candidate[self.edit_dot_index] = new_dot
        else:
            candidate.append(new_dot)
        candidate = self.dedupeIntersectionsByGeometricPoint(candidate)

        ok, msg = self.validateBasicIntersectionPlacement(candidate)
        if not ok:
            self.flashInvalidPlacementMessage(self.validationMessageForUser(msg))
            self.mode = "face"
            self.clearEdgeEditState()
            if not self.isNetViewActive():
                self.restoreFaceViewTarget()
            self.updateCanvas()
            return False

        self.split_mode = False
        self.intersections = candidate
        self.exitToCube()
        return True

    def shiftCurrentEdgeT(self, delta):
        if self.isEdgeMode() and self.current_edge_key is not None:
            (p0x, _), (p1x, _) = self.projectEdgeEndpointPoints(self.current_edge_key)
            direction_sign = 1 if p1x > p0x else -1
            delta *= direction_sign

        self.current_t = self.clamp01(self.current_t + delta)
        self.updateCanvas()

    def setCurrentEdgeT(self, value):
        self.current_t = self.clamp01(value)
        self.updateCanvas()
