import math
from typing import TYPE_CHECKING

import numpy as np

from .constants import FACE_CAMERA_DISTANCE

class CubeRotationMixin:
    current_quat: np.ndarray
    current_rotation: np.ndarray
    face_down_vectors: dict
    face_edge_pseudo: dict
    face_normals: dict
    face_view_rotation: np.ndarray
    selected_face: int | None
    target_camera_distance: float
    target_quat: np.ndarray

    if TYPE_CHECKING:
        def rollForPseudoIndex(self, _pseudo_index: int) -> float: ...

    @staticmethod
    def normalizeVec(vector):
        vector = np.array(vector, dtype=float)
        norm = np.linalg.norm(vector)
        if norm < 1e-8:
            return vector.copy()
        return vector / norm

    @staticmethod
    def orthonormalizeRotation(rotation):
        u, _, vh = np.linalg.svd(np.array(rotation, dtype=float))
        orthonormal_rotation = u @ vh
        if np.linalg.det(orthonormal_rotation) < 0.0:
            u[:, -1] *= -1.0
            orthonormal_rotation = u @ vh
        return orthonormal_rotation

    @staticmethod
    def quatNormalize(quaternion):
        quaternion = np.array(quaternion, dtype=float)
        norm = np.linalg.norm(quaternion)
        if norm < 1e-12:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        return quaternion / norm

    def quatFromMatrix(self, rotation):
        rotation = np.array(rotation, dtype=float)
        trace = rotation[0, 0] + rotation[1, 1] + rotation[2, 2]

        if trace > 0.0:
            scale = math.sqrt(trace + 1.0) * 2.0
            w = 0.25 * scale
            x = (rotation[2, 1] - rotation[1, 2]) / scale
            y = (rotation[0, 2] - rotation[2, 0]) / scale
            z = (rotation[1, 0] - rotation[0, 1]) / scale
        elif rotation[0, 0] > rotation[1, 1] and rotation[0, 0] > rotation[2, 2]:
            scale = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
            w = (rotation[2, 1] - rotation[1, 2]) / scale
            x = 0.25 * scale
            y = (rotation[0, 1] + rotation[1, 0]) / scale
            z = (rotation[0, 2] + rotation[2, 0]) / scale
        elif rotation[1, 1] > rotation[2, 2]:
            scale = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
            w = (rotation[0, 2] - rotation[2, 0]) / scale
            x = (rotation[0, 1] + rotation[1, 0]) / scale
            y = 0.25 * scale
            z = (rotation[1, 2] + rotation[2, 1]) / scale
        else:
            scale = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
            w = (rotation[1, 0] - rotation[0, 1]) / scale
            x = (rotation[0, 2] + rotation[2, 0]) / scale
            y = (rotation[1, 2] + rotation[2, 1]) / scale
            z = 0.25 * scale

        return self.quatNormalize(np.array([w, x, y, z], dtype=float))

    def quatToMatrix(self, quaternion):
        quaternion = self.quatNormalize(quaternion)
        w, x, y, z = quaternion

        xx = x * x
        yy = y * y
        zz = z * z
        xy = x * y
        xz = x * z
        yz = y * z
        wx = w * x
        wy = w * y
        wz = w * z

        return np.array([
            [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz),       2.0 * (xz + wy)],
            [2.0 * (xy + wz),       1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
            [2.0 * (xz - wy),       2.0 * (yz + wx),       1.0 - 2.0 * (xx + yy)],
        ], dtype=float)

    def quatSphericalInterpolate(self, q0, q1, t):
        q0 = self.quatNormalize(q0)
        q1 = self.quatNormalize(q1)

        dot = float(np.dot(q0, q1))
        if dot < 0.0:
            q1 = -q1
            dot = -dot

        if dot > 0.9995:
            quaternion = q0 + t * (q1 - q0)
            return self.quatNormalize(quaternion)

        theta_0 = math.acos(max(-1.0, min(1.0, dot)))
        theta = theta_0 * t
        s0 = math.sin(theta_0 - theta) / math.sin(theta_0)
        s1 = math.sin(theta) / math.sin(theta_0)

        quaternion = s0 * q0 + s1 * q1
        return self.quatNormalize(quaternion)

    def quatAngleTo(self, q0, q1):
        q0 = self.quatNormalize(q0)
        q1 = self.quatNormalize(q1)
        dot = abs(float(np.dot(q0, q1)))
        dot = max(-1.0, min(1.0, dot))
        return 2.0 * math.acos(dot)

    def rotationAxisAngle(self, axis, angle_rad):
        axis = self.normalizeVec(axis)
        if np.linalg.norm(axis) < 1e-8:
            return np.eye(3)

        x, y, z = axis
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        one_minus_c = 1.0 - c

        return np.array([
            [c + x * x * one_minus_c, x * y * one_minus_c - z * s, x * z * one_minus_c + y * s],
            [y * x * one_minus_c + z * s, c + y * y * one_minus_c, y * z * one_minus_c - x * s],
            [z * x * one_minus_c - y * s, z * y * one_minus_c + x * s, c + z * z * one_minus_c],
        ], dtype=float)

    @staticmethod
    def rotX(angle_deg):
        angle = math.radians(angle_deg)
        c, s = math.cos(angle), math.sin(angle)
        return np.array([
            [1, 0, 0],
            [0, c, -s],
            [0, s, c],
        ], dtype=float)

    @staticmethod
    def rotY(angle_deg):
        angle = math.radians(angle_deg)
        c, s = math.cos(angle), math.sin(angle)
        return np.array([
            [c, 0, s],
            [0, 1, 0],
            [-s, 0, c],
        ], dtype=float)

    def cubeRotationMatrix(self, pitch_deg, yaw_deg):
        return self.rotX(pitch_deg) @ self.rotY(yaw_deg)

    def setCurrentQuat(self, quaternion):
        self.current_quat = self.quatNormalize(quaternion)
        self.current_rotation = self.quatToMatrix(self.current_quat)

    def setTargetRotation(self, rotation):
        rotation = self.orthonormalizeRotation(rotation)
        self.target_quat = self.quatFromMatrix(rotation)

    @staticmethod
    def normalizeAngle(angle):
        while angle <= -180.0:
            angle += 360.0
        while angle > 180.0:
            angle -= 360.0
        return angle

    @staticmethod
    def signedAngleAroundAxis(v_from, v_to, axis):
        v_from = np.array(v_from, dtype=float)
        v_to = np.array(v_to, dtype=float)
        axis = np.array(axis, dtype=float)

        if np.linalg.norm(v_from) < 1e-8 or np.linalg.norm(v_to) < 1e-8 or np.linalg.norm(axis) < 1e-8:
            return 0.0

        v_from /= np.linalg.norm(v_from)
        v_to /= np.linalg.norm(v_to)
        axis /= np.linalg.norm(axis)

        cross = np.cross(v_from, v_to)
        sin_a = np.dot(axis, cross)
        cos_a = np.clip(np.dot(v_from, v_to), -1.0, 1.0)
        return math.atan2(sin_a, cos_a)

    def rotationFromVectors(self, v_from, v_to):
        v_from = self.normalizeVec(v_from)
        v_to = self.normalizeVec(v_to)

        cross = np.cross(v_from, v_to)
        dot = np.clip(np.dot(v_from, v_to), -1.0, 1.0)
        if np.linalg.norm(cross) < 1e-8:
            if dot > 0.999999:
                return np.eye(3)

            axis = np.array([1.0, 0.0, 0.0], dtype=float)
            if abs(v_from[0]) > 0.9:
                axis = np.array([0.0, 1.0, 0.0], dtype=float)
            axis = axis - np.dot(axis, v_from) * v_from
            axis = self.normalizeVec(axis)
            return self.rotationAxisAngle(axis, math.pi)

        axis = self.normalizeVec(cross)
        angle = math.acos(dot)
        return self.rotationAxisAngle(axis, angle)

    def makeFaceViewRotationFromCurrent(self, face_index):
        current_rotation = self.current_rotation
        view_forward = np.array([0.0, 0.0, -1.0], dtype=float)
        screen_down = np.array([0.0, -1.0, 0.0], dtype=float)
        screen_up = np.array([0.0, 1.0, 0.0], dtype=float)

        local_normal = self.face_normals[face_index]
        world_normal = current_rotation @ local_normal
        align_rotation = self.rotationFromVectors(world_normal, view_forward)
        face_rotation = self.orthonormalizeRotation(align_rotation @ current_rotation)

        local_down = self.face_down_vectors[face_index]
        world_down = face_rotation @ local_down
        world_down_proj = world_down - np.dot(world_down, view_forward) * view_forward

        if np.linalg.norm(world_down_proj) > 1e-8:
            angle_to_down = self.signedAngleAroundAxis(world_down_proj, screen_down, view_forward)
            angle_to_up = self.signedAngleAroundAxis(world_down_proj, screen_up, view_forward)
            roll_delta = angle_to_down if abs(angle_to_down) <= abs(angle_to_up) else angle_to_up
            roll_rotation = self.rotationAxisAngle(view_forward, roll_delta)
            target_rotation = roll_rotation @ face_rotation
        else:
            target_rotation = face_rotation

        return self.orthonormalizeRotation(target_rotation)

    def restoreFaceViewTarget(self):
        self.setTargetRotation(self.face_view_rotation)
        self.target_camera_distance = FACE_CAMERA_DISTANCE

    def setEdgeViewTarget(self, edge_index):
        pseudo_map = self.face_edge_pseudo.get(self.selected_face, {})
        pseudo_index = pseudo_map.get(edge_index, 0)
        roll_deg = self.rollForPseudoIndex(pseudo_index)

        view_axis = np.array([0.0, 0.0, -1.0], dtype=float)
        roll_rotation = self.rotationAxisAngle(view_axis, math.radians(roll_deg))
        target_rotation = roll_rotation @ self.face_view_rotation

        self.setTargetRotation(target_rotation)
        self.target_camera_distance = FACE_CAMERA_DISTANCE
