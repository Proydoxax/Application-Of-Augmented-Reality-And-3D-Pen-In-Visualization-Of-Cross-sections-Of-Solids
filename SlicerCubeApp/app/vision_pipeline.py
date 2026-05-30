import cv2
import numpy as np

from .constants import (
    BLACK_HSV_LOWER,
    BLACK_HSV_UPPER,
    MASK_KERNEL_SHAPE,
    RED_HSV_RANGES,
)


def rgbaToBgr(frame_rgba: np.ndarray) -> np.ndarray:
    if frame_rgba is None or frame_rgba.size == 0:
        raise ValueError("Empty RGBA frame.")
    return cv2.cvtColor(frame_rgba, cv2.COLOR_RGBA2BGR)


def bgrToRgb(frame_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def cleanTemplateMask(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones(MASK_KERNEL_SHAPE, np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def buildRedMaskFromHsv(hsv: np.ndarray) -> np.ndarray:
    red_masks = [cv2.inRange(hsv, lower, upper) for lower, upper in RED_HSV_RANGES]
    red_mask = red_masks[0]
    for mask in red_masks[1:]:
        red_mask = cv2.bitwise_or(red_mask, mask)
    return cleanTemplateMask(red_mask)


def buildRedMaskFromBgr(frame_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    return buildRedMaskFromHsv(hsv)


def normalizeFrameRgba(frame_rgba: np.ndarray, build_display: bool = True) -> dict:
    frame_bgr = rgbaToBgr(frame_rgba)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    black_mask = cleanTemplateMask(cv2.inRange(hsv, BLACK_HSV_LOWER, BLACK_HSV_UPPER))
    red_mask = buildRedMaskFromHsv(hsv)
    structure_mask = cv2.bitwise_or(black_mask, red_mask)

    processed = {
        "black_mask": black_mask,
        "red_mask": red_mask,
        "structure_mask": structure_mask,
        "frame_bgr": frame_bgr,
        "hsv": hsv,
    }
    if build_display:
        display_bgr = np.full_like(frame_bgr, 255)
        display_bgr[black_mask > 0] = (0, 0, 0)
        display_bgr[red_mask > 0] = (0, 0, 255)
        processed["display_rgb"] = bgrToRgb(display_bgr)
    return processed


def rgbToKivyTextureData(frame_rgb: np.ndarray) -> tuple[bytes, int, int]:
    if frame_rgb is None or frame_rgb.size == 0:
        raise ValueError("Empty RGB frame.")

    flipped = np.flipud(frame_rgb)
    h, w, _ = flipped.shape
    return flipped.tobytes(), w, h
