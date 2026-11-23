"""Frame preparation (Sect. 3.3.1) and the night/fog augmentation used for training."""
import cv2
import numpy as np


def mean_brightness(bgr):
    return float(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 2].mean())


def apply_clahe(bgr, clip_limit=2.0, tile_grid=8):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def maybe_clahe(bgr, clahe_cfg, force=None):
    """Applies CLAHE to low-light frames only. Returns (frame, applied)."""
    use = clahe_cfg.get("enabled", True) if force is None else force
    if use and (force or mean_brightness(bgr) < clahe_cfg.get("brightness_threshold", 70)):
        return apply_clahe(bgr, clahe_cfg.get("clip_limit", 2.0), clahe_cfg.get("tile_grid", 8)), True
    return bgr, False


def apply_roi(bgr, roi_polygon):
    """Blacks out sky and shoreline outside the region of interest."""
    if not roi_polygon:
        return bgr
    mask = np.zeros(bgr.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.asarray(roi_polygon, np.int32)], 255)
    return cv2.bitwise_and(bgr, bgr, mask=mask)


def darken(bgr, rng):
    """Night-like copy: gamma darkening, a slight blue cast and sensor noise."""
    gamma = rng.uniform(1.8, 3.0)
    out = 255.0 * (bgr.astype(np.float32) / 255.0) ** gamma
    out *= rng.uniform(0.45, 0.7)
    out[..., 0] *= 1.08
    out += rng.normal(0, 4.0, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def add_haze(bgr, rng):
    """Fog-like copy from the atmospheric scattering model I = J·t + A·(1 − t)."""
    t = rng.uniform(0.35, 0.65)
    airlight = rng.uniform(190, 235)
    out = bgr.astype(np.float32) * t + airlight * (1.0 - t)
    return np.clip(out, 0, 255).astype(np.uint8)


def dark_channel_mean(bgr, patch=15):
    """High values indicate haze/fog (dark channel prior); used to tag fog frames automatically."""
    dark = cv2.erode(bgr.min(axis=2), np.ones((patch, patch), np.uint8))
    return float(dark.mean())


def guess_condition(bgr, night_brightness=60, fog_dark_channel=110):
    if mean_brightness(bgr) < night_brightness:
        return "night"
    if dark_channel_mean(bgr) > fog_dark_channel:
        return "fog"
    return "day"
