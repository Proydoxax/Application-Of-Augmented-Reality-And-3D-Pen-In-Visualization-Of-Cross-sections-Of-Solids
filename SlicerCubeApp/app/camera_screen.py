try:
    import cv2
except Exception as e:
    raise RuntimeError(f"cv2 import failed: {e}")

try:
    import numpy as np
except Exception as e:
    raise RuntimeError(f"numpy import failed: {e}")

from collections import Counter, deque
from collections.abc import Callable
from itertools import product
from threading import Lock
import time

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.utils import platform

try:
    from camera4kivy import Preview
except Exception as e:
    raise RuntimeError(f"camera4kivy import failed: {e}")

try:
    from .vision_pipeline import normalizeFrameRgba
    from .net_detector import detectRectangularFaceQuads, extractFaceWarps, warpFace
    from .red_detector import classifyFaceRedMark, detectRedSegmentEndpoints
    from .constants import (
        FACE_INDEX_TO_NAME,
        FACE_SCAN_SEQUENCE,
        MANUAL_GUIDE_SIDE_RATIO,
        pointOnEdgeKey,
    )
    from .cube_mapper import (
        assignCrossNetFaces,
        mapDetectedPointsToEntries,
        entriesToText,
        printedTToCanonicalT,
        canonicalObservationsToEntries,
        filterEntriesToValidSection,
    )
except Exception as e:
    raise RuntimeError(f"detector import failed: {e}")


def formatFaceLabel(face_name: str) -> str:
    return str(face_name).upper()


def pointCount(count: int) -> str:
    return f"{count} {'point' if count == 1 else 'points'}"


def convertToSignature(entry: dict):
    raw_edge_key = tuple(entry.get("edge_key", ()))
    canonical_t = entry.get("canonical_t")
    if len(raw_edge_key) != 2 or canonical_t is None:
        return None

    try:
        edge_key = (int(raw_edge_key[0]), int(raw_edge_key[1]))
        point_t = float(canonical_t)
    except (TypeError, ValueError):
        return None

    try:
        px, py, pz = pointOnEdgeKey(edge_key, point_t)
    except IndexError:
        return "edge", edge_key, round(point_t, 2)
    return "point", round(px, 3), round(py, 3), round(pz, 3)


class _DetectionStabilityMixin:
    on_detected: Callable[[dict], None] | None
    on_display_rect: Callable[[tuple[float, float, float, float]], None] | None
    on_manual_capture: Callable[[dict], None] | None
    on_manual_alignment: Callable[[bool], None] | None
    on_status: Callable[[str], None] | None
    auto_enabled: bool
    detect_every_n_frames: int
    display_every_n_frames: int
    display_rect: tuple[float, float, float, float] | None
    frame_counter: int
    fresh_display_frames: int
    history: deque
    ignore_until_time: float
    manual_alignment_every_n_frames: int
    manual_capture_frame_count: int
    manual_face_aligned: bool
    manual_request: dict | None
    max_valid_scan_wait: int
    min_fresh_display_frames: int
    payload_history: deque
    required_stable_scans: int
    result_sent: bool
    warmup_frames: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_sent = False
        self.auto_enabled = True
        self.manual_request = None

        self.frame_counter = 0
        self.warmup_frames = 18
        self.display_every_n_frames = 2
        self.detect_every_n_frames = 4
        self.ignore_until_time = 0.0
        self.fresh_display_frames = 0
        self.min_fresh_display_frames = 2
        self.display_rect = None

        self.history = deque(maxlen=10)
        self.payload_history = deque(maxlen=10)
        self.required_stable_scans = 2
        self.max_valid_scan_wait = 6
        self.manual_capture_frame_count = 4
        self.manual_alignment_every_n_frames = 4
        self.manual_face_aligned = False

    def resetStability(self):
        self.history.clear()
        self.payload_history.clear()

    def setStatus(self, text: str):
        if self.on_status:
            Clock.schedule_once(lambda _dt: self.on_status(text), 0)

    def setVisibleFacesStatus(self, count: int):
        self.setStatus(f"Visible faces: {max(0, min(int(count), 6))}/6.")

    def setDisplayRect(self, pos, size):
        rect: tuple[float, float, float, float] = (
            float(pos[0]),
            float(pos[1]),
            float(size[0]),
            float(size[1]),
        )
        old = self.display_rect
        if old is not None and all(abs(float(a) - float(b)) <= 0.5 for a, b in zip(old, rect)):
            return
        self.display_rect = rect
        if self.on_display_rect:
            self.on_display_rect(rect)

    def setAutoEnabled(self, enabled: bool):
        self.auto_enabled = bool(enabled)
        if self.auto_enabled:
            self.manual_request = None
            self.setManualAlignment(False)
        self.resetStability()

    def resumeAfterRejectedResult(self):
        self.result_sent = False
        self.manual_request = None
        self.ignore_until_time = time.monotonic() + 0.65
        self.resetStability()

    def requestManualCapture(self, face_name: str, face_index: int):
        self.manual_request = {
            "face_name": face_name,
            "face_index": int(face_index),
            "results": [],
        }
        self.setStatus(f"Capturing {formatFaceLabel(face_name)}...")

    def cancelManualCapture(self):
        if self.manual_request is None:
            return False
        self.manual_request = None
        return True

    def sendManualCaptureResult(self, result: dict):
        if self.on_manual_capture:
            def dispatchManualCapture(_dt):
                self.on_manual_capture(result)

            Clock.schedule_once(dispatchManualCapture, 0)

    @staticmethod
    def manualFacePointsFromMark(mark: dict) -> list[dict]:
        points = []
        for hit in mark.get("boundary_hits") or []:
            try:
                edge = int(hit["edge"])
                t = float(hit["edge_t"])
            except (KeyError, TypeError, ValueError):
                continue
            if not 0 <= edge < 4 or t < -0.02 or t > 1.02:
                continue
            points.append({"edge": edge, "t": max(0.0, min(1.0, t))})
        return points

    @staticmethod
    def manualLineSignature(points: list[dict]):
        if len(points) != 2:
            return None
        try:
            return tuple(sorted(int(point["edge"]) for point in points))
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def manualMedianFacePoints(points_per_frame: list[list[dict]]) -> list[dict]:
        ordered_frames = [
            sorted(points, key=lambda point: (int(point["edge"]), float(point["t"])))
            for points in points_per_frame
        ]
        if not ordered_frames:
            return []

        point_count = len(ordered_frames[0])
        if point_count == 0 or any(len(points) != point_count for points in ordered_frames):
            return []

        median_points = []
        for point_index in range(point_count):
            edge_values = {int(points[point_index]["edge"]) for points in ordered_frames}
            if len(edge_values) != 1:
                return []
            median_points.append({
                "edge": edge_values.pop(),
                "t": float(np.median([float(points[point_index]["t"]) for points in ordered_frames])),
            })
        return median_points

    @staticmethod
    def manualCaptureRejected(face_name: str | None, detail: str):
        label = f"{formatFaceLabel(face_name)}: " if face_name else ""
        return {
            "ok": False,
            "mark_kind": "invalid",
            "message": f"{label}{detail}",
            "face_points": [],
            "observations": [],
        }

    @staticmethod
    def manualObservationsFromFacePoints(face_name: str, face_index: int, face_points: list[dict]) -> list[dict]:
        observations = []
        for face_point in face_points:
            edge = int(face_point["edge"])
            t = float(face_point["t"])
            if t < -0.02 or t > 1.02:
                continue
            t = max(0.0, min(1.0, t))
            if t <= 0.08:
                t = 0.0
            elif t >= 0.92:
                t = 1.0
            edge_key, canonical_t = printedTToCanonicalT(face_index, edge, t)
            observations.append({
                "edge_key": edge_key,
                "canonical_t": canonical_t,
                "source_face_name": face_name,
                "source_face_index": face_index,
                "source_edge": edge,
                "source_t": t,
            })
        return observations

    def manualCaptureFromFacePoints(
        self,
        face_name: str,
        face_index: int,
        mark_kind: str,
        face_points: list[dict],
    ):
        expected_count = {"blank": 0, "dot": 1, "line": 2}.get(mark_kind)
        if expected_count is None or len(face_points) != expected_count:
            return self.manualCaptureRejected(face_name, "red mark is unclear. Try again.")

        observations = self.manualObservationsFromFacePoints(face_name, face_index, face_points)
        if len(observations) != expected_count:
            return self.manualCaptureRejected(face_name, "red mark is outside the face boundary. Try again.")

        if mark_kind == "blank":
            message = f"{formatFaceLabel(face_name)} saved: no red mark."
        else:
            message = f"{formatFaceLabel(face_name)} saved: {mark_kind}."
        return {
            "ok": True,
            "mark_kind": mark_kind,
            "message": message,
            "face_name": face_name,
            "face_index": face_index,
            "face_points": face_points,
            "observations": observations,
        }

    def bestManualCaptureResult(self, results: list[dict], face_name: str | None = None):
        if not results or face_name is None:
            return self.manualCaptureRejected(face_name, "capture failed. Try again.")

        good_results = [
            result
            for result in results
            if result.get("ok") and result.get("mark_kind") in {"blank", "line", "dot"}
        ]
        if len(good_results) < 2:
            return self.manualCaptureRejected(face_name, "capture is unclear. Hold steady and try again.")

        mark_counts = Counter(result["mark_kind"] for result in good_results)
        if mark_counts["line"] and mark_counts["dot"]:
            return self.manualCaptureRejected(face_name, "line and dot frames disagree. Try again.")

        mark_kind, mark_count = mark_counts.most_common(1)[0]
        if mark_count * 2 <= len(good_results):
            return self.manualCaptureRejected(face_name, "frames disagree. Try again.")
        required_support = len(results) // 2 + 1
        if mark_count < required_support:
            return self.manualCaptureRejected(face_name, f"not enough clear {mark_kind} frames. Try again.")
        if mark_kind == "blank":
            return self.manualCaptureFromFacePoints(face_name, int(results[0]["face_index"]), "blank", [])

        if mark_kind == "line":
            line_signatures = Counter(
                self.manualLineSignature(result.get("face_points") or [])
                for result in good_results
                if result.get("mark_kind") == "line"
            )
            line_signatures.pop(None, None)
            if not line_signatures:
                return self.manualCaptureRejected(face_name, "line endpoints are unclear. Try again.")

            edge_signature, edge_count = line_signatures.most_common(1)[0]
            if edge_count * 2 <= len(good_results):
                return self.manualCaptureRejected(face_name, "line frames disagree on the face edges. Try again.")

            line_frames = [
                result
                for result in good_results
                if result.get("mark_kind") == "line"
                and self.manualLineSignature(result.get("face_points") or []) == edge_signature
            ]
            median_points = self.manualMedianFacePoints(
                [result.get("face_points") or [] for result in line_frames]
            )
            if len(median_points) != 2:
                return self.manualCaptureRejected(face_name, "line endpoints are unclear. Try again.")
            return self.manualCaptureFromFacePoints(
                face_name,
                int(results[0]["face_index"]),
                "line",
                median_points,
            )

        dot_edges = Counter(
            int((result.get("face_points") or [{}])[0]["edge"])
            for result in good_results
            if result.get("mark_kind") == "dot" and len(result.get("face_points") or []) == 1
        )
        if not dot_edges:
            return self.manualCaptureRejected(face_name, "dot position is unclear. Try again.")

        dot_edge, dot_count = dot_edges.most_common(1)[0]
        if dot_count * 2 <= len(good_results):
            return self.manualCaptureRejected(face_name, "dot frames disagree on the face edge. Try again.")

        dot_frames = [
            result
            for result in good_results
            if result.get("mark_kind") == "dot"
            and len(result.get("face_points") or []) == 1
            and int(result["face_points"][0]["edge"]) == dot_edge
        ]
        dot_ts = [float(result["face_points"][0]["t"]) for result in dot_frames]
        if max(dot_ts) - min(dot_ts) > 0.18:
            return self.manualCaptureRejected(face_name, "dot frames disagree on the edge position. Try again.")
        return self.manualCaptureFromFacePoints(
            face_name,
            int(results[0]["face_index"]),
            "dot",
            [{"edge": dot_edge, "t": float(np.median(dot_ts))}],
        )

    def captureManualFrame(self, processed: dict):
        request = self.manual_request
        if request is None:
            return None

        face_name = request["face_name"]
        face_index = int(request["face_index"])
        results = request["results"]
        results.append(self.captureManualFaceFromFrame(processed, face_name, face_index))

        frame_count = max(2, int(getattr(self, "manual_capture_frame_count", 4)))
        if len(results) < frame_count:
            return None

        self.manual_request = None
        return self.bestManualCaptureResult(results, face_name)

    def setManualAlignment(self, aligned: bool):
        aligned = bool(aligned)
        if aligned == self.manual_face_aligned:
            return
        self.manual_face_aligned = aligned
        if self.on_manual_alignment:
            Clock.schedule_once(lambda _dt, ready=aligned: self.on_manual_alignment(ready), 0)

    def cameraReadyForDetection(self) -> bool:
        return (
            self.frame_counter > self.warmup_frames
            and time.monotonic() >= self.ignore_until_time
            and self.fresh_display_frames >= self.min_fresh_display_frames
        )

    def shouldUpdateManualAlignment(self) -> bool:
        if self.auto_enabled or self.manual_request is not None:
            return False
        cadence = max(1, int(getattr(self, "manual_alignment_every_n_frames", 4)))
        return self.frame_counter % cadence == 0

    @staticmethod
    def convertEntriesToSignature(entries):
        items = []
        for item in entries:
            edge_key = tuple(item.get("edge_key", ()))
            canonical_t = item.get("canonical_t", None)
            if edge_key and canonical_t is not None:
                stable_t = round(float(canonical_t) / 0.10) * 0.10
                sig = ("ek", edge_key, round(stable_t, 1))
            else:
                stable_t = round(float(item.get("t", 0.0)) / 0.10) * 0.10
                sig = (
                    "fe",
                    int(item.get("face_index", -1)),
                    int(item.get("edge", -1)),
                    round(stable_t, 1),
                )
            items.append(sig)
        return tuple(sorted(items))

    @staticmethod
    def countPayloadPoints(payload):
        points = set()
        for item in payload.get("entries") or []:
            signature = convertToSignature(item)
            if signature is not None:
                points.add(signature)
        return len(points)

    def findPayloadBySignature(self, signature):
        for old_sig, old_payload in reversed(self.payload_history):
            if old_sig == signature:
                return old_payload
        return None

    def chooseBestRecentPayload(self):
        if not self.payload_history:
            return None
        best_payload = None
        best_score = float("-inf")
        for age, (_sig, payload) in enumerate(self.payload_history):
            point_count = self.countPayloadPoints(payload)
            entry_count = len(payload.get("entries") or [])

            score = 100.0 * point_count + entry_count + 0.01 * age
            if score > best_score:
                best_score = score
                best_payload = payload
        return best_payload

    def chooseStablePayloadWhenReady(self, payload):
        sig = self.convertEntriesToSignature(payload["entries"])
        self.history.append(sig)
        self.payload_history.append((sig, payload))

        max_wait = int(getattr(self, "max_valid_scan_wait", 6))
        counts = Counter(self.history)
        best_sig, best_count = counts.most_common(1)[0]
        required = int(getattr(self, "required_stable_scans", 2))

        if len(self.history) < max_wait:
            self.setStatus(f"Hold steady... {len(self.history)}/{max_wait}")
            return None

        if best_count >= required:
            stable = self.findPayloadBySignature(best_sig)
            best_recent = self.chooseBestRecentPayload()
            if best_recent is not None and self.countPayloadPoints(best_recent) > self.countPayloadPoints(stable or {}):
                return best_recent
            return stable or best_recent

        return self.chooseBestRecentPayload()

    @staticmethod
    def buildDetectionPayload(assigned_faces, entries):
        text = entriesToText(entries, one_based=True)
        return {
            "entries": entries,
            "text": text,
            "assigned_faces": assigned_faces,
        }

    def runTemplateDetectionPipeline(self, processed: dict):
        faces = detectRectangularFaceQuads(
            processed["black_mask"],
            processed.get("red_mask"),
            max_candidates=16,
        )
        self.setVisibleFacesStatus(len(faces))
        if len(faces) < 6:
            return None

        assigned_faces = assignCrossNetFaces(faces)
        if not assigned_faces:
            return None

        assigned_items = list(assigned_faces.items())
        enriched_faces = extractFaceWarps(
            processed["frame_bgr"],
            [face for _, face in assigned_items],
            size=256,
        )
        assigned_faces = {
            face_name: enriched
            for (face_name, _), enriched in zip(assigned_items, enriched_faces)
        }
        for face in assigned_faces.values():
            face["red_detection"] = detectRedSegmentEndpoints(face["warp_bgr"])

        entries = filterEntriesToValidSection(
            mapDetectedPointsToEntries(assigned_faces),
            plane_tol=0.04,
        )
        if not entries:
            return None

        unique_points = set()
        for item in entries:
            signature = convertToSignature(item)
            if signature is not None:
                unique_points.add(signature)

        if len(unique_points) < 3:
            return None
        if len(unique_points) > 6:
            return None

        payload = self.buildDetectionPayload(assigned_faces, entries)
        stable_payload = self.chooseStablePayloadWhenReady(payload)
        if stable_payload is None:
            return None

        return stable_payload

    @staticmethod
    def chooseBestManualFaceCandidate(faces, frame_shape):
        if not faces:
            return None
        h, w = frame_shape[:2]
        cx0, cy0 = w * 0.5, h * 0.5

        def score(face):
            cx, cy = face["center"]
            dx = (float(cx) - cx0) / max(w, 1)
            dy = (float(cy) - cy0) / max(h, 1)
            central_penalty = (dx * dx + dy * dy) ** 0.5
            area_bonus = min(float(face.get("area", 0.0)) / max(w * h, 1), 0.25)
            quality = float(face.get("quality", 0.0))
            return central_penalty - area_bonus - 0.15 * quality

        return sorted(faces, key=score)[0]

    @staticmethod
    def manualGuideBoxBounds(frame_shape):
        h, w = frame_shape[:2]
        side = min(float(w), float(h)) * MANUAL_GUIDE_SIDE_RATIO
        x0 = (float(w) - side) / 2.0
        y0 = (float(h) - side) / 2.0
        return x0, y0, x0 + side, y0 + side, side

    @staticmethod
    def manualGuideBoxCorners(frame_shape):
        x0, y0, x1, y1, _side = _DetectionStabilityMixin.manualGuideBoxBounds(frame_shape)
        return np.array(
            [
                [x0, y0],
                [x1, y0],
                [x1, y1],
                [x0, y1],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def measureManualGuideEdgeSupport(mask: np.ndarray, frame_shape) -> list[float]:
        if mask is None or mask.size == 0:
            return []

        h, w = mask.shape[:2]
        x0, y0, x1, y1, side = _DetectionStabilityMixin.manualGuideBoxBounds(frame_shape)
        points = [
            (int(round(x0)), int(round(y0))),
            (int(round(x1)), int(round(y0))),
            (int(round(x1)), int(round(y1))),
            (int(round(x0)), int(round(y1))),
        ]
        border_thickness = max(2, int(round(side * 0.025)))
        support_thickness = max(4, int(round(side * 0.055)))
        support = cv2.dilate(
            (mask > 0).astype(np.uint8) * 255,
            np.ones((support_thickness, support_thickness), np.uint8),
            iterations=1,
        )

        scores = []
        for index, p0 in enumerate(points):
            edge = np.zeros((h, w), dtype=np.uint8)
            cv2.line(edge, p0, points[(index + 1) % 4], 255, border_thickness)
            edge_pixels = edge > 0
            total = int(np.count_nonzero(edge_pixels))
            if total <= 0:
                scores.append(0.0)
                continue
            covered = int(np.count_nonzero((support > 0) & edge_pixels))
            scores.append(covered / float(total))
        return scores

    @staticmethod
    def manualFaceFitsGuideBox(candidate: dict, processed: dict) -> bool:
        try:
            face_cx, face_cy = map(float, candidate["center"])
        except (KeyError, TypeError, ValueError):
            return False

        frame_shape = processed["frame_bgr"].shape
        x0, y0, x1, y1, side = _DetectionStabilityMixin.manualGuideBoxBounds(frame_shape)
        center_fit = (
            x0 - side * 0.14 <= face_cx <= x1 + side * 0.14
            and y0 - side * 0.14 <= face_cy <= y1 + side * 0.14
        )
        edge_scores = _DetectionStabilityMixin.measureManualGuideEdgeSupport(
            processed.get("structure_mask"),
            frame_shape,
        )
        touched_edges = sum(score >= 0.14 for score in edge_scores)
        enough_border_support = touched_edges >= 3 and sum(edge_scores) >= 0.82
        return bool(center_fit and enough_border_support)

    def findManualFaceCandidate(self, processed: dict):
        faces = detectRectangularFaceQuads(
            processed["black_mask"],
            processed.get("red_mask"),
            min_area=220,
            max_area_ratio=0.98,
            max_candidates=16,
        )
        if not faces:
            return None, False

        candidate = self.chooseBestManualFaceCandidate(faces, processed["frame_bgr"].shape)
        return candidate, self.manualFaceFitsGuideBox(candidate, processed)

    def updateManualAlignment(self, processed: dict):
        if self.auto_enabled:
            self.setManualAlignment(False)
            return
        _candidate, aligned = self.findManualFaceCandidate(processed)
        self.setManualAlignment(aligned)

    def captureManualFaceFromFrame(self, processed: dict, face_name: str, face_index: int):
        candidate, aligned = self.findManualFaceCandidate(processed)
        if candidate is None or not aligned:
            return {
                "ok": False,
                "mark_kind": "invalid",
                "message": f"{formatFaceLabel(face_name)}: align one face in the square.",
                "face_name": face_name,
                "face_index": face_index,
                "face_points": [],
                "observations": [],
            }

        guide_warp = warpFace(
            processed["frame_bgr"],
            self.manualGuideBoxCorners(processed["frame_bgr"].shape),
            size=256,
        )
        mark = classifyFaceRedMark(guide_warp)
        if str(mark.get("kind", "invalid")) == "invalid":
            enriched = extractFaceWarps(processed["frame_bgr"], [candidate], size=256)[0]
            exact_warp = warpFace(processed["frame_bgr"], enriched["ordered_quad"], size=256)
            mark = classifyFaceRedMark(exact_warp)
            if str(mark.get("kind", "invalid")) == "invalid":
                mark = classifyFaceRedMark(enriched["warp_bgr"])
        mark_kind = str(mark.get("kind", "invalid"))
        face_points = self.manualFacePointsFromMark(mark)
        expected_count = {"blank": 0, "dot": 1, "line": 2}.get(mark_kind)
        if expected_count is None or len(face_points) != expected_count:
            return {
                "ok": False,
                "mark_kind": "invalid",
                "message": f"{formatFaceLabel(face_name)}: red mark is unclear in this frame.",
                "face_name": face_name,
                "face_index": face_index,
                "face_points": [],
                "observations": [],
            }

        return {
            "ok": True,
            "mark_kind": mark_kind,
            "message": f"{formatFaceLabel(face_name)}: {mark_kind} frame captured.",
            "face_name": face_name,
            "face_index": face_index,
            "face_points": face_points,
            "observations": [],
        }

class AnalyzerPreview(_DetectionStabilityMixin, Preview):
    def __init__(
        self,
        on_detected=None,
        on_status=None,
        on_manual_capture=None,
        on_manual_alignment=None,
        on_display_rect=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.on_detected = on_detected
        self.on_status = on_status
        self.on_manual_capture = on_manual_capture
        self.on_manual_alignment = on_manual_alignment
        self.on_display_rect = on_display_rect

        self.lock = Lock()
        self.pending_rgb_bytes = None
        self.pending_size = None
        self.processed_texture = None

        self.connected = False

        self.setVisibleFacesStatus(0)

    def startCapture(self):
        self.resetForNewScan()
        self.connectForAnalysis()

    def resetForNewScan(self):
        self.result_sent = False
        self.frame_counter = 0
        self.manual_request = None
        self.setManualAlignment(False)
        self.ignore_until_time = time.monotonic() + 0.75
        self.fresh_display_frames = 0
        self.resetStability()
        with self.lock:
            self.pending_rgb_bytes = None
            self.pending_size = None
        self.processed_texture = None
        self.setVisibleFacesStatus(0)

    def stopCapture(self):
        self.disconnectSafely()

    def connectForAnalysis(self):
        if self.connected:
            self.disconnectSafely()
        try:
            self.connect_camera(
                camera_id="back",
                mirrored=False,
                enable_analyze_pixels=True,
                analyze_pixels_resolution=720,
                enable_video=False,
                enable_photo=False,
            )
            self.connected = True
            self.setVisibleFacesStatus(0)
        except Exception as exc:
            self.connected = False
            self.setStatus(f"Camera error: {exc}")

    def disconnectSafely(self):
        if not self.connected:
            return

        # noinspection PyBroadException
        try:
            self.disconnect_camera()
        except Exception:
            pass
        finally:
            self.connected = False
            self.setStatus("Camera disconnected.")

    def analyzePixelsCallback(self, pixels, size, _image_pos, _image_scale, _mirror):
        width, height = size
        try:
            self.frame_counter += 1
            self.fresh_display_frames += 1
            ready_for_detection = self.cameraReadyForDetection()
            should_detect = (
                self.manual_request is not None
                or (
                    self.auto_enabled
                    and ready_for_detection
                    and self.frame_counter % self.detect_every_n_frames == 0
                )
            )
            should_update_alignment = self.shouldUpdateManualAlignment()
            if not should_detect and not should_update_alignment:
                return

            frame_rgba = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)
            processed = normalizeFrameRgba(frame_rgba, build_display=False)
            if should_update_alignment:
                self.updateManualAlignment(processed)

            if not should_detect:
                return

            if self.manual_request is not None:
                result = self.captureManualFrame(processed)
                if result is not None:
                    self.sendManualCaptureResult(result)
                return

            if not self.auto_enabled or self.result_sent:
                return

            stable_payload = self.runTemplateDetectionPipeline(processed)
            if stable_payload is None:
                return
            self.result_sent = True
            if self.on_detected:
                Clock.schedule_once(lambda _dt: self.on_detected(stable_payload), 0)
        except Exception as exc:
            self.setStatus(f"Scan error: {exc}")

    def canvasInstructionsCallback(self, texture, tex_size, tex_pos):
        draw_texture = texture
        if draw_texture is None:
            self.promotePendingTexture()
            draw_texture = self.processed_texture
        if draw_texture is not None:
            draw_pos = tex_pos if tex_pos is not None else self.pos
            draw_size = tex_size if tex_size is not None else self.size
            Color(1, 1, 1, 1)
            Rectangle(texture=draw_texture, size=draw_size, pos=draw_pos)
            self.setDisplayRect(draw_pos, draw_size)

    def promotePendingTexture(self):
        with self.lock:
            if self.pending_rgb_bytes is None or self.pending_size is None:
                return
            raw = self.pending_rgb_bytes
            tex_w, tex_h = self.pending_size
            self.pending_rgb_bytes = None
            self.pending_size = None
        if self.processed_texture is None or self.processed_texture.size != (tex_w, tex_h):
            # noinspection PyArgumentList
            self.processed_texture = Texture.create(size=(tex_w, tex_h), colorfmt="rgb")
        self.processed_texture.blit_buffer(raw, colorfmt="rgb", bufferfmt="ubyte")


class ManualFaceGuide(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(size_hint=(1, 1), pos_hint={"x": 0, "y": 0}, **kwargs)
        self.active = False
        self.aligned = False
        self.display_rect = None
        self.bind(pos=self.redraw, size=self.redraw)

    def setDisplayRect(self, rect):
        try:
            clean_rect = tuple(float(value) for value in rect[:4])
        except (TypeError, ValueError):
            clean_rect = None
        if clean_rect == self.display_rect:
            return
        self.display_rect = clean_rect
        self.redraw()

    def setActive(self, active: bool):
        active = bool(active)
        if self.active == active:
            return
        self.active = active
        if not active:
            self.aligned = False
        self.redraw()

    def setAligned(self, aligned: bool):
        aligned = bool(aligned)
        if self.aligned == aligned:
            return
        self.aligned = aligned
        self.redraw()

    def guideBox(self):
        if self.display_rect is not None:
            base_x, base_y, base_width, base_height = self.display_rect
        else:
            base_x, base_y, base_width, base_height = self.x, self.y, self.width, self.height

        side = min(float(base_width), float(base_height)) * MANUAL_GUIDE_SIDE_RATIO
        side = min(side, max(1.0, float(base_width) - dp(24)), max(1.0, float(base_height) - dp(24)))
        side = max(dp(60), side)
        side = min(side, max(1.0, float(base_width)), max(1.0, float(base_height)))
        x0 = float(base_x) + (float(base_width) - side) / 2.0
        y0 = float(base_y) + (float(base_height) - side) / 2.0
        return x0, y0, side

    def redraw(self, *_):
        self.canvas.clear()
        if not self.active or self.width <= 0 or self.height <= 0:
            return

        x0, y0, side = self.guideBox()
        with self.canvas:
            if self.aligned:
                Color(0.0, 1.0, 0.22, 0.12)
                Rectangle(pos=(x0, y0), size=(side, side))
                Color(0.0, 1.0, 0.22, 0.22)
                Line(rectangle=(x0, y0, side, side), width=dp(7))
                Color(0.18, 1.0, 0.35, 1.0)
                Line(rectangle=(x0, y0, side, side), width=dp(2.2))
            else:
                Color(0.0, 0.0, 0.0, 0.88)
                Line(rectangle=(x0, y0, side, side), width=dp(1.8))


class ManualFaceReviewTile(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(None, None),
            size=(dp(116), dp(116)),
            pos_hint={"x": 0.02, "top": 0.98},
            opacity=0.0,
            disabled=True,
            **kwargs,
        )
        self.face_points = []
        self.bind(pos=self.redraw, size=self.redraw, opacity=self.redraw)

    def clearFace(self):
        self.face_points = []
        self.opacity = 0.0
        self.redraw()

    def showFace(self, face_points: list[dict]):
        clean_points = []
        for point in face_points or []:
            try:
                edge = int(point["edge"])
                t = float(point["t"])
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= edge < 4:
                clean_points.append({"edge": edge, "t": max(0.0, min(1.0, t))})
        self.face_points = clean_points
        self.opacity = 1.0
        self.redraw()

    @staticmethod
    def pointOnPreviewEdge(edge: int, t: float, x0: float, y0: float, side: float):
        t = max(0.0, min(1.0, float(t)))
        if edge == 0:
            return x0 + side * t, y0 + side
        if edge == 1:
            return x0 + side, y0 + side * (1.0 - t)
        if edge == 2:
            return x0 + side * t, y0
        return x0, y0 + side * (1.0 - t)

    def redraw(self, *_):
        self.canvas.clear()
        if self.opacity <= 0.0 or self.width <= 0 or self.height <= 0:
            return

        pad = dp(11)
        side = max(dp(32), min(self.width, self.height) - 2.0 * pad)
        x0 = self.x + (self.width - side) / 2.0
        y0 = self.y + (self.height - side) / 2.0
        draw_points = [
            self.pointOnPreviewEdge(int(point["edge"]), float(point["t"]), x0, y0, side)
            for point in self.face_points
        ]

        with self.canvas:
            Color(0.0, 0.0, 0.0, 0.30)
            RoundedRectangle(
                pos=(self.x + dp(3), self.y + dp(2)),
                size=(max(0.0, self.width - dp(6)), max(0.0, self.height - dp(6))),
                radius=[dp(5)],
            )
            Color(1.0, 1.0, 1.0, 0.98)
            Rectangle(pos=(x0, y0), size=(side, side))
            Color(0.03, 0.03, 0.03, 1.0)
            Line(rectangle=(x0, y0, side, side), width=dp(1.7))
            if len(draw_points) >= 2:
                Color(0.92, 0.0, 0.0, 1.0)
                Line(points=[value for point in draw_points for value in point], width=dp(3.2))
            for px, py in draw_points:
                radius = dp(4.2)
                Color(0.92, 0.0, 0.0, 1.0)
                Ellipse(pos=(px - radius, py - radius), size=(radius * 2.0, radius * 2.0))


class CameraScreen(BoxLayout):
    def __init__(self, on_result=None, on_validate=None, on_close=None, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(4), padding=dp(2), **kwargs)
        self.on_result = on_result
        self.on_validate = on_validate
        self.on_close = on_close
        self.manual_mode = False
        self.manual_index = 0
        self.manual_observations = []
        self.manual_face_reviews = {}
        self.manual_confirmation_pending = False
        self.pending_result_payload = None
        self.detection_fade_event = None
        self.detection_fade_start_event = None
        self.status_label = Label(
            text="Starting camera...",
            size_hint_y=None,
            height=dp(52),
            halign="center",
            valign="middle",
            font_size=dp(13),
        )
        self.status_label.bind(size=lambda *_: setattr(self.status_label, "text_size", self.status_label.size))

        if platform != "android":
            raise RuntimeError("Camera scanning is available only in Android builds.")

        self.preview = AnalyzerPreview(
            on_detected=self.handleResult,
            on_status=self.setStatus,
            on_manual_capture=self.handleManualCapture,
            on_manual_alignment=self.setManualAlignment,
            on_display_rect=self.setManualDisplayRect,
            aspect_ratio="4:3",
        )

        self.preview.size_hint = (1, 1)
        self.preview.pos_hint = {"x": 0, "y": 0}
        try:
            self.preview.allow_stretch = True
            self.preview.keep_ratio = True
            self.preview.fit_mode = "contain"
        except AttributeError:
            pass

        self.preview_container = FloatLayout(size_hint=(1, 1))
        self.preview_container.add_widget(self.preview)
        self.manual_guide = ManualFaceGuide()
        self.preview_container.add_widget(self.manual_guide)
        self.manual_review_tile = ManualFaceReviewTile()
        self.preview_container.add_widget(self.manual_review_tile)

        self.detection_message = Label(
            text="Layout detected",
            color=(0.0, 1.0, 0.15, 1.0),
            bold=True,
            font_size=dp(26),
            opacity=0.0,
            size_hint=(1, None),
            height=dp(80),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="center",
            valign="middle",
        )
        self.detection_message.bind(size=lambda *_: setattr(self.detection_message, "text_size", self.detection_message.size))
        self.detection_message.bind(pos=self.redrawDetectionMessageBackground, size=self.redrawDetectionMessageBackground, opacity=self.redrawDetectionMessageBackground)
        self.preview_container.add_widget(self.detection_message)
        self.add_widget(self.preview_container)

        self.rescan_controls = BoxLayout(size_hint_y=None, height=0, spacing=dp(6), opacity=0.0, disabled=True)
        self.btn_rescan_previous = Button(text="Undo previous face", disabled=True)
        self.btn_rescan_previous.bind(on_press=self.rescanPreviousFace)
        self.rescan_controls.add_widget(self.btn_rescan_previous)
        self.add_widget(self.rescan_controls)

        controls = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.btn_close = Button(text="Close")
        self.btn_close.bind(on_press=self.closeSelf)
        controls.add_widget(self.btn_close)

        self.btn_manual = Button(text="Face-by-face")
        self.btn_manual.bind(on_press=self.toggleManualMode)
        controls.add_widget(self.btn_manual)

        self.btn_capture = Button(text="Capture", disabled=True)
        self.btn_capture.bind(on_press=self.captureManualFace)
        self.btn_capture.bind(on_release=self.releaseManualCapture)
        controls.add_widget(self.btn_capture)

        self.btn_skip = Button(text="Skip", disabled=True)
        self.btn_skip.bind(on_press=self.skipManualFace)
        controls.add_widget(self.btn_skip)

        self.add_widget(controls)
        self.add_widget(self.status_label)

    def setStatus(self, text: str):
        self.status_label.text = text

    def setManualAlignment(self, aligned: bool):
        if hasattr(self, "manual_guide"):
            self.manual_guide.setAligned(bool(aligned) and self.manual_mode)

    def setManualDisplayRect(self, rect):
        if hasattr(self, "manual_guide"):
            self.manual_guide.setDisplayRect(rect)

    def updateManualCaptureButton(self):
        if not hasattr(self, "btn_capture"):
            return
        if self.manual_mode and self.manual_confirmation_pending:
            self.btn_capture.text = "Confirm"
        elif self.manual_mode:
            self.btn_capture.text = "Hold Capture"
        else:
            self.btn_capture.text = "Capture"

    def setManualConfirmationPending(self, pending: bool):
        self.manual_confirmation_pending = bool(pending)
        self.updateManualCaptureButton()

    def clearManualFaceReviews(self):
        self.manual_face_reviews = {}
        if hasattr(self, "manual_review_tile"):
            self.manual_review_tile.clearFace()

    def rememberManualFaceReview(self, result: dict):
        try:
            face_index = int(result["face_index"])
        except (KeyError, TypeError, ValueError):
            return

        review = {
            "face_name": str(result.get("face_name") or ""),
            "mark_kind": str(result.get("mark_kind") or ""),
            "face_points": [
                {"edge": int(point["edge"]), "t": float(point["t"])}
                for point in result.get("face_points") or []
                if isinstance(point, dict) and "edge" in point and "t" in point
            ],
        }
        self.manual_face_reviews[face_index] = review
        self.manual_review_tile.showFace(review["face_points"])

    def showLatestManualFaceReview(self):
        scanned_faces = FACE_SCAN_SEQUENCE[:max(0, min(self.manual_index, len(FACE_SCAN_SEQUENCE)))]
        for _face_name, face_index in reversed(scanned_faces):
            review = self.manual_face_reviews.get(int(face_index))
            if review is not None:
                self.manual_review_tile.showFace(review.get("face_points") or [])
                return
        self.manual_review_tile.clearFace()

    def setScanButtonsDisabled(self, disabled: bool):
        for button in (self.btn_close, self.btn_manual, self.btn_capture, self.btn_skip):
            button.disabled = bool(disabled)
        if disabled:
            self.btn_rescan_previous.disabled = True
        else:
            self.updateRescanPreviousButton()

    def setRescanPreviousVisible(self, visible: bool):
        visible = bool(visible)
        self.rescan_controls.height = dp(44) if visible else 0
        self.rescan_controls.opacity = 1.0 if visible else 0.0
        self.rescan_controls.disabled = not visible
        self.updateRescanPreviousButton()

    def updateRescanPreviousButton(self):
        if not hasattr(self, "btn_rescan_previous"):
            return
        manual_capture_pending = getattr(self.preview, "manual_request", None) is not None
        self.btn_rescan_previous.disabled = bool(
            not self.manual_mode
            or self.manual_index <= 0
            or self.pending_result_payload is not None
            or manual_capture_pending
        )

    def redrawDetectionMessageBackground(self, *_):
        self.detection_message.canvas.before.clear()
        alpha = float(self.detection_message.opacity)
        if alpha <= 0.0:
            return
        x = self.detection_message.x + dp(18)
        y = self.detection_message.y + dp(12)
        w = max(0, self.detection_message.width - dp(36))
        h = max(0, self.detection_message.height - dp(24))
        with self.detection_message.canvas.before:
            Color(1, 1, 1, alpha)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(12)])
            Color(0, 0, 0, alpha)
            Line(rounded_rectangle=(x, y, w, h, dp(12)), width=dp(2))

    def showDetectionMessage(self, text: str, color: tuple[float, float, float, float]):
        self.cancelDetectionFade()
        self.detection_message.text = text
        self.detection_message.color = color
        self.detection_message.opacity = 1.0
        self.redrawDetectionMessageBackground()

    def startCamera(self):
        self.pending_result_payload = None
        self.cancelDetectionFade()
        self.detection_message.opacity = 0.0
        self.redrawDetectionMessageBackground()
        self.setScanButtonsDisabled(False)
        self.btn_capture.disabled = not self.manual_mode
        self.btn_skip.disabled = not self.manual_mode
        self.updateManualCaptureButton()
        self.updateRescanPreviousButton()
        self.preview.startCapture()

    def stopCamera(self):
        self.preview.stopCapture()

    def closeSelf(self, *_):
        self.pending_result_payload = None
        self.cancelDetectionFade()
        self.stopCamera()
        if self.on_close:
            self.on_close()

    def cancelDetectionFade(self):
        if self.detection_fade_start_event is not None:
            self.detection_fade_start_event.cancel()
            self.detection_fade_start_event = None
        if self.detection_fade_event is not None:
            self.detection_fade_event.cancel()
            self.detection_fade_event = None

    def scheduleDetectionMessageFade(self, delay: float):
        if self.detection_fade_start_event is not None:
            self.detection_fade_start_event.cancel()
        self.detection_fade_start_event = Clock.schedule_once(
            lambda _dt: self.startDetectionMessageFade(),
            delay,
        )

    def currentManualFaceTarget(self):
        return FACE_SCAN_SEQUENCE[self.manual_index]

    def toggleManualMode(self, *_):
        if self.pending_result_payload is not None:
            return
        self.manual_mode = not self.manual_mode
        self.manual_index = 0
        self.manual_observations = []
        self.clearManualFaceReviews()
        self.setManualConfirmationPending(False)
        self.preview.setAutoEnabled(not self.manual_mode)
        self.manual_guide.setActive(self.manual_mode)
        self.manual_guide.setAligned(False)
        self.setRescanPreviousVisible(self.manual_mode)
        self.btn_capture.disabled = not self.manual_mode
        self.btn_skip.disabled = not self.manual_mode
        self.btn_manual.text = "Auto scan" if self.manual_mode else "Face-by-face"
        self.updateManualCaptureButton()
        if self.manual_mode:
            face_name, _ = self.currentManualFaceTarget()
            self.setStatus(f"{formatFaceLabel(face_name)}: align in the square. Hold Capture or Skip.")
        else:
            self.setStatus("Auto scan on. Show the full template.")

    def captureManualFace(self, *_):
        if self.pending_result_payload is not None:
            return
        if not self.manual_mode:
            return
        if self.manual_confirmation_pending:
            self.confirmManualScan()
            return
        face_name, face_index = self.currentManualFaceTarget()
        self.btn_skip.disabled = True
        self.btn_manual.disabled = True
        self.btn_rescan_previous.disabled = True
        self.preview.requestManualCapture(face_name, face_index)

    def releaseManualCapture(self, *_):
        if not self.manual_mode or self.pending_result_payload is not None or self.manual_confirmation_pending:
            return
        if not hasattr(self.preview, "cancelManualCapture"):
            return
        if not self.preview.cancelManualCapture():
            return
        self.btn_skip.disabled = False
        self.btn_manual.disabled = False
        self.updateRescanPreviousButton()
        face_name, _ = self.currentManualFaceTarget()
        self.setStatus(f"Hold the button until {formatFaceLabel(face_name)} is scanned.")

    def rescanPreviousFace(self, *_):
        if not self.manual_mode or self.pending_result_payload is not None or self.manual_index <= 0:
            return

        previous_name, previous_index = FACE_SCAN_SEQUENCE[self.manual_index - 1]
        self.manual_index -= 1
        self.manual_observations = [
            observation for observation in self.manual_observations
            if int(observation.get("source_face_index", -1)) != int(previous_index)
        ]
        self.manual_face_reviews.pop(int(previous_index), None)
        self.setManualConfirmationPending(False)
        self.btn_capture.disabled = False
        self.btn_skip.disabled = False
        self.btn_manual.disabled = False
        self.showLatestManualFaceReview()
        self.updateRescanPreviousButton()
        self.setStatus(f"{formatFaceLabel(previous_name)} undone. Align it in the square and hold Capture.")

    def skipManualFace(self, *_):
        if self.pending_result_payload is not None:
            return
        if not self.manual_mode or self.manual_confirmation_pending:
            return
        face_name, _ = self.currentManualFaceTarget()
        self.setStatus(f"{formatFaceLabel(face_name)} skipped.")
        self.advanceToNextManualFace()

    def confirmManualScan(self, *_):
        if (
            not self.manual_mode
            or not self.manual_confirmation_pending
            or self.pending_result_payload is not None
        ):
            return
        self.btn_capture.disabled = True
        self.btn_skip.disabled = True
        self.btn_manual.disabled = True
        self.btn_rescan_previous.disabled = True
        self.setStatus("Finishing face-by-face scan...")
        Clock.schedule_once(lambda _dt: self.finishManualScan(), 0)

    @staticmethod
    def rotateManualFacePoint(edge: int, t: float, turns: int):
        edge = int(edge)
        t = max(0.0, min(1.0, float(t)))
        if edge == 0:
            x, y = t, 0.0
        elif edge == 1:
            x, y = 1.0, t
        elif edge == 2:
            x, y = t, 1.0
        else:
            x, y = 0.0, t

        for _ in range(int(turns) % 4):
            x, y = 1.0 - y, x

        tol = 1e-7
        if abs(y) <= tol:
            return 0, x
        if abs(x - 1.0) <= tol:
            return 1, y
        if abs(y - 1.0) <= tol:
            return 2, x
        return 3, y

    def buildManualObservationsForFaceRotations(self, face_turns: dict[int, int]):
        rotated = []
        for observation in self.manual_observations:
            try:
                face_index = int(observation["source_face_index"])
                source_edge = int(observation["source_edge"])
                source_t = float(observation["source_t"])
            except (KeyError, TypeError, ValueError):
                continue

            edge, t = self.rotateManualFacePoint(
                source_edge,
                source_t,
                int(face_turns.get(face_index, 0)),
            )
            face_name = str(observation.get("source_face_name") or FACE_INDEX_TO_NAME[face_index])
            edge_key, canonical_t = printedTToCanonicalT(face_index, edge, t)
            rotated.append({
                "edge_key": edge_key,
                "canonical_t": canonical_t,
                "source_face_name": face_name,
                "source_face_index": face_index,
                "source_edge": edge,
                "source_t": t,
            })
        return rotated

    @staticmethod
    def countManualEntryPoints(entries: list[dict]) -> int:
        signatures = set()
        for entry in entries:
            signature = convertToSignature(entry)
            if signature is not None:
                signatures.add(signature)
        return len(signatures)

    def chooseManualEntriesForBestFaceRotations(self):
        face_indices = sorted({
            int(observation["source_face_index"])
            for observation in self.manual_observations
            if "source_face_index" in observation
        })
        if not face_indices:
            return []

        raw_candidates = []
        seen_raw_signatures = set()
        for turns in product(range(4), repeat=len(face_indices)):
            face_turns = dict(zip(face_indices, turns))
            observations = self.buildManualObservationsForFaceRotations(face_turns)
            raw_entries = canonicalObservationsToEntries(observations)
            raw_points = self.countManualEntryPoints(raw_entries)
            if raw_points < 3:
                continue

            raw_signature = tuple(
                (
                    tuple(entry.get("edge_key", ())),
                    round(float(entry.get("canonical_t", 0.0)), 3),
                )
                for entry in raw_entries
            )
            if raw_signature in seen_raw_signatures:
                continue
            seen_raw_signatures.add(raw_signature)

            merged_support = sum(max(0, int(entry.get("merged_count", 1)) - 1) for entry in raw_entries)
            unchanged_faces = sum(int(turn == 0) for turn in turns)
            raw_score = (
                int(raw_points <= 6),
                merged_support,
                -max(0, raw_points - 6),
                unchanged_faces,
                raw_points,
            )
            raw_candidates.append((raw_score, raw_entries, raw_points, merged_support, unchanged_faces))

        raw_candidates.sort(key=lambda item: item[0], reverse=True)
        best_score = None
        best_entries = []
        for _raw_score, raw_entries, raw_points, merged_support, unchanged_faces in raw_candidates[:36]:
            entries = filterEntriesToValidSection(raw_entries, plane_tol=0.04)
            point_count = self.countManualEntryPoints(entries)
            if not 3 <= point_count <= 6:
                continue

            preserved_points = int(point_count == raw_points and raw_points <= 6)
            dropped_points = max(0, raw_points - point_count)
            score = (
                preserved_points,
                merged_support,
                -dropped_points,
                point_count,
                unchanged_faces,
            )
            if best_score is None or score > best_score:
                best_score = score
                best_entries = entries
        return best_entries

    def handleManualCapture(self, result: dict):
        if not self.manual_mode:
            return
        self.btn_capture.disabled = False
        self.btn_skip.disabled = False
        self.btn_manual.disabled = False
        self.updateRescanPreviousButton()
        if not result.get("ok"):
            self.setStatus(result.get("message", "Capture failed. Try again."))
            return
        self.manual_observations.extend(result.get("observations", []))
        self.rememberManualFaceReview(result)
        self.setStatus(result.get("message", "Face saved."))
        self.advanceToNextManualFace(wait_for_confirmation=True)

    def advanceToNextManualFace(self, wait_for_confirmation: bool = False):
        self.manual_index += 1
        if self.manual_index >= len(FACE_SCAN_SEQUENCE):
            if wait_for_confirmation:
                self.setManualConfirmationPending(True)
                self.btn_capture.disabled = False
                self.btn_skip.disabled = True
                self.btn_manual.disabled = False
                self.updateRescanPreviousButton()
                self.setStatus("Last face saved. Confirm the scan or undo that face.")
            else:
                self.finishManualScan()
            return
        face_name, _ = self.currentManualFaceTarget()
        self.setManualConfirmationPending(False)
        self.updateRescanPreviousButton()
        self.setStatus(f"{formatFaceLabel(face_name)}: align in the square. Hold Capture. {pointCount(len(self.manual_observations))} saved.")

    def restartManualScanAfterInvalidResult(self, status_text: str):
        self.setStatus(status_text)
        self.manual_index = 0
        self.manual_observations = []
        self.clearManualFaceReviews()
        self.setManualConfirmationPending(False)
        self.btn_capture.disabled = False
        self.btn_skip.disabled = False
        self.btn_manual.disabled = False
        self.updateRescanPreviousButton()

    def finishManualScan(self):
        entries = canonicalObservationsToEntries(self.manual_observations)
        unique = set()
        for item in entries:
            signature = convertToSignature(item)
            if signature is not None:
                unique.add(signature)
        if len(unique) < 3:
            self.restartManualScanAfterInvalidResult(f"Only {len(unique)}/3 dots found. Try closer.")
            return
        if len(unique) > 6:
            self.restartManualScanAfterInvalidResult(f"Too many dots ({len(unique)}). Skip blank faces.")
            return

        payload = {
            "entries": entries,
            "text": entriesToText(entries, one_based=True),
            "assigned_faces": {},
        }
        self.handleResult(payload)

    def handleResult(self, payload: dict):
        if self.pending_result_payload is not None:
            return

        if self.on_validate is not None and not self.on_validate(payload):
            self.pending_result_payload = None
            if self.manual_mode:
                self.manual_index = 0
                self.manual_observations = []
                self.clearManualFaceReviews()
                self.setManualConfirmationPending(False)
            self.setScanButtonsDisabled(False)
            self.btn_capture.disabled = not self.manual_mode
            self.btn_skip.disabled = not self.manual_mode
            self.setStatus("Try again! Hold the template steady.")
            self.showDetectionMessage("Try again!", (1.0, 0.0, 0.0, 1.0))
            if hasattr(self.preview, "resumeAfterRejectedResult"):
                self.preview.resumeAfterRejectedResult()
            self.scheduleDetectionMessageFade(0.7)
            return

        self.pending_result_payload = payload
        self.setStatus("Layout detected.")
        self.setScanButtonsDisabled(True)
        self.showDetectionMessage("Layout detected", (0.0, 1.0, 0.15, 1.0))

        self.scheduleDetectionMessageFade(1.0)

    def startDetectionMessageFade(self):
        self.detection_fade_start_event = None
        self.cancelDetectionFade()
        self.detection_fade_event = Clock.schedule_interval(self.fadeDetectionMessage, 1.0 / 30.0)

    def fadeDetectionMessage(self, dt):
        self.detection_message.opacity = max(0.0, self.detection_message.opacity - dt / 0.55)
        self.redrawDetectionMessageBackground()
        if self.detection_message.opacity > 0.0:
            return True

        self.cancelDetectionFade()
        payload = self.pending_result_payload
        self.pending_result_payload = None
        if payload is None:
            return False
        self.stopCamera()
        if payload is not None and self.on_result:
            self.on_result(payload)
        return False


class CameraPopup(Popup):
    def __init__(self, on_result=None, on_validate=None, **kwargs):
        super().__init__(
            title="Scan Template",
            size_hint=(0.98, 0.98),
            auto_dismiss=False,
            **kwargs,
        )
        self.screen = CameraScreen(on_result=on_result, on_validate=on_validate, on_close=self.dismiss)
        self.content = self.screen

    def onOpen(self):
        Clock.schedule_once(lambda _dt: self.screen.startCamera(), 0)

    def onPreDismiss(self):
        self.screen.stopCamera()
