import os

import numpy as np
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.utils import platform

# Root controls
ROW_HEIGHT = dp(40)
TEXT_HEIGHT = dp(100)

# platform
IS_ANDROID = platform == "android"

# fonts
VIGA_FONT_NAME = "Viga"
CANVAS_FONT_ALIAS = "Roboto"

# cube interaction
DRAG_THRESHOLD = 5.0
EDGE_PICK_THRESHOLD = 25.0
EDGE_PICK_EXTEND = 1.0
DOT_PICK_THRESHOLD = 15.0
IGNORED_TOUCH_BUTTONS = ("right", "scroll" + "up", "scroll" + "down")

# cube projectuing
ANGLE_EPSILON = 0.1
DISTANCE_EPSILON = 0.01
PROJECTION_SCALE = 0.8
FACE_CAMERA_DISTANCE = 3.0
CUBE_CAMERA_DISTANCE = 5.0

# cube overlay
DOT_RADIUS = dp(4)
ACTIVE_DOT_RADIUS = dp(6)
EDGE_LABEL_OFFSET_CUBE = 20.0
EDGE_LABEL_OFFSET_FACE = 30.0
DOT_LABEL_OFFSET = dp(18)
BOTTOM_T_LABEL_Y = dp(24)
INVALID_PLACEMENT_MESSAGE = "INVALID PLACEMENT: POINTS MUST LIE ON THE SAME PLANE"

NET_2D_LAYOUT = {
    4: (1, 0),
    1: (1, 1),
    2: (0, 2),
    5: (1, 2),
    3: (2, 2),
    0: (1, 3),
}
NET_2D_ROWS = 4
NET_2D_COLS = 3
NET_2D_GAP_RATIO = 0.12

MANUAL_GUIDE_SIDE_RATIO = 0.29

BLACK_HSV_LOWER = (0, 0, 0)
BLACK_HSV_UPPER = (180, 255, 120)
RED_HSV_RANGES = (
    ((0, 70, 45), (14, 255, 255)),
    ((166, 70, 45), (180, 255, 255)),
)
MASK_KERNEL_SHAPE = (3, 3)

CUBE_VERTICES = (
    (-1, -1, -1),  # 0
    (-1, -1, 1),   # 1
    (-1, 1, -1),   # 2
    (-1, 1, 1),    # 3
    (1, -1, -1),   # 4
    (1, -1, 1),    # 5
    (1, 1, -1),    # 6
    (1, 1, 1),     # 7
)

CUBE_EDGES = (
    (0, 1), (0, 2), (0, 4),
    (3, 1), (3, 2), (3, 7),
    (5, 1), (5, 4), (5, 7),
    (6, 2), (6, 4), (6, 7),
)

CUBE_FACES = (
    (1, 3, 7, 5),
    (0, 2, 6, 4),
    (0, 1, 3, 2),
    (4, 5, 7, 6),
    (2, 3, 7, 6),
    (0, 1, 5, 4),
)

CUBE_FACE_VERTICES = {index: list(face) for index, face in enumerate(CUBE_FACES)}
FACE_EDGE_CORNER_INDICES = (
    (0, 1),  # top, left to right
    (1, 2),  # right, top to bottom
    (3, 2),  # bottom, left to right
    (0, 3),  # left, top to bottom
)

# face 1 = front
# face 2 = back
# face 3 = left
# face 4 = right
# face 5 = top
# face 6 = bottom

FACE_NORMALS = {
    0: np.array([0.0, 0.0, 1.0]),
    1: np.array([0.0, 0.0, -1.0]),
    2: np.array([-1.0, 0.0, 0.0]),
    3: np.array([1.0, 0.0, 0.0]),
    4: np.array([0.0, 1.0, 0.0]),
    5: np.array([0.0, -1.0, 0.0]),
}

FACE_DOWN_VECTORS = {
    0: np.array([0.0, -1.0, 0.0]),
    1: np.array([0.0, -1.0, 0.0]),
    2: np.array([0.0, -1.0, 0.0]),
    3: np.array([0.0, -1.0, 0.0]),
    4: np.array([0.0, 0.0, 1.0]),
    5: np.array([0.0, 0.0, -1.0]),
}

CUBE_VERTEX_VECTORS = tuple(np.array(vertex, dtype=float) for vertex in CUBE_VERTICES)
VALID_EDGE_KEYS = frozenset((min(a, b), max(a, b)) for a, b in CUBE_EDGES)
FACE_CENTERS = tuple(
    tuple(sum(CUBE_VERTICES[index][axis] for index in face) / len(face) for axis in range(3))
    for face in CUBE_FACES
)

PRINTED_FACE_VERTICES = {
    0: [1, 5, 7, 3],  # front: A B F E
    1: [2, 6, 4, 0],  # back: H G C D
    2: [2, 0, 1, 3],  # left: H D A E
    3: [4, 6, 7, 5],  # right: C G F B
    4: [3, 7, 6, 2],  # top: E F G H
    5: [0, 4, 5, 1],  # bottom: D C B A
}

FACE_NAME_TO_INDEX = {
    "front": 0,
    "back": 1,
    "left": 2,
    "right": 3,
    "top": 4,
    "bottom": 5,
}
FACE_INDEX_TO_NAME = {index: name for name, index in FACE_NAME_TO_INDEX.items()}
NET_FACE_NAMES = ("top", "back", "left", "bottom", "right", "front")
FACE_SCAN_SEQUENCE = tuple((face_name, FACE_NAME_TO_INDEX[face_name]) for face_name in NET_FACE_NAMES)


def vigaFontCandidates():
    base_dir = os.path.dirname(__file__)
    return (
        os.path.join(base_dir, "fonts", "Viga-Regular.ttf"),
    )


def findVigaFontPath():
    for path in vigaFontCandidates():
        if os.path.exists(path):
            return path
    return None


def registerVigaFont():
    path = findVigaFontPath()
    if path is None:
        return None
    try:
        LabelBase.register(name=VIGA_FONT_NAME, fn_regular=path)
        return VIGA_FONT_NAME
    except Exception:
        return None


def canvasFontName():
    path = findVigaFontPath()
    if path is None:
        return CANVAS_FONT_ALIAS
    try:
        LabelBase.register(name=CANVAS_FONT_ALIAS, fn_regular=path)
        return CANVAS_FONT_ALIAS
    except Exception:
        return path


CANVAS_FONT_NAME = canvasFontName()


def parseFaceEdgeRows(data: str, face_count: int = 6, edge_count: int = 4):
    entries = []

    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue

        for part in line.split(";"):
            piece = part.strip()
            if piece:
                entries.append(piece)

    parsed_rows = []
    for entry in entries:
        try:
            face_str, edge_str, t_str = [part.strip() for part in entry.split(",")]
            face = int(face_str)
            edge = int(edge_str)
            t = float(t_str)
        except ValueError:
            continue

        if 1 <= face <= face_count and 1 <= edge <= edge_count:
            face -= 1
            edge -= 1

        if not (0 <= face < face_count and 0 <= edge < edge_count and 0.0 <= t <= 1.0):
            continue

        parsed_rows.append((face, edge, t))

    return parsed_rows


def clamp01(value) -> float:
    return max(0.0, min(1.0, float(value)))


def canonicalEdgeKey(v0: int, v1: int) -> tuple[int, int]:
    return (v0, v1) if v0 < v1 else (v1, v0)


def edgeKeyFromFaceEdge(face_index: int, edge_index: int) -> tuple[int, int]:
    face_vertices = CUBE_FACES[face_index]
    v0 = face_vertices[edge_index % 4]
    v1 = face_vertices[(edge_index + 1) % 4]
    return canonicalEdgeKey(v0, v1)


def orientedFaceEdgeVertices(face_index: int, edge_index: int) -> tuple[int, int]:
    face_vertices = CUBE_FACES[face_index]
    start_index, end_index = FACE_EDGE_CORNER_INDICES[edge_index % 4]
    return face_vertices[start_index], face_vertices[end_index]


def faceEdgeTToCanonicalT(face_index: int, edge_index: int, t: float) -> float:
    v0, v1 = orientedFaceEdgeVertices(face_index, edge_index)
    edge_key = canonicalEdgeKey(v0, v1)
    t = clamp01(t)
    return t if (v0, v1) == edge_key else 1.0 - t


def canonicalTToFaceEdgeT(face_index: int, edge_index: int, t: float) -> float:
    return faceEdgeTToCanonicalT(face_index, edge_index, t)


def pointOnEdgeKey(edge_key: tuple[int, int], t: float) -> tuple[float, float, float]:
    v0, v1 = edge_key
    x0, y0, z0 = CUBE_VERTICES[v0]
    x1, y1, z1 = CUBE_VERTICES[v1]
    t = float(t)
    return (
        (1.0 - t) * x0 + t * x1,
        (1.0 - t) * y0 + t * y1,
        (1.0 - t) * z0 + t * z1
    )
