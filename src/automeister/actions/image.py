"""Image recognition actions using OpenCV template matching."""

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from automeister.actions import mouse, screen


class MatchMethod(Enum):
    """OpenCV template matching methods."""

    CCOEFF = cv2.TM_CCOEFF
    CCOEFF_NORMED = cv2.TM_CCOEFF_NORMED
    CCORR = cv2.TM_CCORR
    CCORR_NORMED = cv2.TM_CCORR_NORMED
    SQDIFF = cv2.TM_SQDIFF
    SQDIFF_NORMED = cv2.TM_SQDIFF_NORMED


# Methods where minimum value is best match
SQDIFF_METHODS = {MatchMethod.SQDIFF, MatchMethod.SQDIFF_NORMED}

# Default method for template matching
DEFAULT_METHOD = MatchMethod.CCOEFF_NORMED


@dataclass
class MatchResult:
    """Result of a template match."""

    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        """Get the center point of the match."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "center_x": self.center[0],
            "center_y": self.center[1],
        }


class ImageNotFoundError(Exception):
    """Raised when a template image is not found on screen."""

    def __init__(self, template_path: str, timeout: float | None = None) -> None:
        self.template_path = template_path
        self.timeout = timeout
        if timeout:
            msg = f"Image '{template_path}' not found after {timeout}s"
        else:
            msg = f"Image '{template_path}' not found on screen"
        super().__init__(msg)


def _load_image(path: str) -> np.ndarray:
    """Load an image file as a numpy array."""
    img_path = Path(path).expanduser().resolve()
    if not img_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Failed to load image: {path}")

    return img


def _capture_screen_as_array(
    region: tuple[int, int, int, int] | None = None,
) -> np.ndarray:
    """Capture the screen and return as a numpy array."""
    # Capture to temp file
    screenshot_path = screen.capture(region=region)

    # Load as numpy array
    img = cv2.imread(screenshot_path)

    # Clean up temp file
    Path(screenshot_path).unlink(missing_ok=True)

    return img


def find(
    template_path: str,
    threshold: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
    grayscale: bool = False,
    method: MatchMethod = DEFAULT_METHOD,
    match_mode: Literal["best", "first", "all"] = "best",
) -> list[MatchResult]:
    """
    Find a template image on the screen.

    Args:
        template_path: Path to the template image file
        threshold: Minimum confidence threshold (0.0-1.0)
        region: Optional region to search within (x, y, width, height)
        grayscale: Convert images to grayscale before matching
        method: OpenCV matching method
        match_mode: How to handle matches:
            - "best": Return only the best match
            - "first": Return first match above threshold
            - "all": Return all matches above threshold

    Returns:
        List of MatchResult objects (empty if no matches found)
    """
    # Load template
    template = _load_image(template_path)
    template_h, template_w = template.shape[:2]

    # Capture screen
    screenshot = _capture_screen_as_array(region)

    # Convert to grayscale if requested
    if grayscale:
        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Perform template matching
    result = cv2.matchTemplate(screenshot, template, method.value)

    # For SQDIFF methods, lower values are better matches
    is_sqdiff = method in SQDIFF_METHODS

    matches: list[MatchResult] = []

    if match_mode == "best":
        # Get best match
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if is_sqdiff:
            confidence = 1.0 - min_val if method == MatchMethod.SQDIFF_NORMED else 1.0
            loc = min_loc
        else:
            confidence = max_val
            loc = max_loc

        if confidence >= threshold:
            # Adjust location if region was specified
            x, y = loc
            if region:
                x += region[0]
                y += region[1]

            matches.append(
                MatchResult(
                    x=x,
                    y=y,
                    width=template_w,
                    height=template_h,
                    confidence=float(confidence),
                )
            )

    elif match_mode in ("first", "all"):
        # Find all locations above threshold
        if is_sqdiff:
            # For SQDIFF, we need values below (1 - threshold)
            if method == MatchMethod.SQDIFF_NORMED:
                locations = np.where(result <= (1.0 - threshold))
            else:
                # For non-normalized, use a heuristic threshold
                locations = np.where(result <= threshold * result.max())
        else:
            locations = np.where(result >= threshold)

        # Convert to list of (y, x) coordinates
        for pt in zip(*locations[::-1], strict=False):
            x, y = int(pt[0]), int(pt[1])

            # Get confidence at this location
            conf = result[y, x]
            if is_sqdiff and method == MatchMethod.SQDIFF_NORMED:
                conf = 1.0 - conf

            # Adjust location if region was specified
            if region:
                x += region[0]
                y += region[1]

            matches.append(
                MatchResult(
                    x=x,
                    y=y,
                    width=template_w,
                    height=template_h,
                    confidence=float(conf),
                )
            )

            if match_mode == "first":
                break

        # Sort by confidence (highest first) for "all" mode
        if match_mode == "all" and matches:
            matches.sort(key=lambda m: m.confidence, reverse=True)

    return matches


def find_best(
    template_path: str,
    threshold: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
    grayscale: bool = False,
    method: MatchMethod = DEFAULT_METHOD,
) -> MatchResult | None:
    """
    Find the best match for a template image on the screen.

    Args:
        template_path: Path to the template image file
        threshold: Minimum confidence threshold (0.0-1.0)
        region: Optional region to search within (x, y, width, height)
        grayscale: Convert images to grayscale before matching
        method: OpenCV matching method

    Returns:
        MatchResult if found, None otherwise
    """
    matches = find(
        template_path,
        threshold=threshold,
        region=region,
        grayscale=grayscale,
        method=method,
        match_mode="best",
    )
    return matches[0] if matches else None


def wait_for(
    template_path: str,
    timeout: float = 30.0,
    interval: float = 0.5,
    threshold: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
    grayscale: bool = False,
    method: MatchMethod = DEFAULT_METHOD,
) -> MatchResult:
    """
    Wait for a template image to appear on the screen.

    Args:
        template_path: Path to the template image file
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        threshold: Minimum confidence threshold (0.0-1.0)
        region: Optional region to search within (x, y, width, height)
        grayscale: Convert images to grayscale before matching
        method: OpenCV matching method

    Returns:
        MatchResult when image is found

    Raises:
        ImageNotFoundError: If image is not found within timeout
    """
    start_time = time.time()

    while True:
        result = find_best(
            template_path,
            threshold=threshold,
            region=region,
            grayscale=grayscale,
            method=method,
        )

        if result:
            return result

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            raise ImageNotFoundError(template_path, timeout)

        time.sleep(interval)


def click_image(
    template_path: str,
    button: Literal["left", "middle", "right"] = "left",
    offset_x: int = 0,
    offset_y: int = 0,
    timeout: float = 0.0,
    interval: float = 0.5,
    threshold: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
    grayscale: bool = False,
    method: MatchMethod = DEFAULT_METHOD,
) -> MatchResult:
    """
    Find a template image and click on it.

    Args:
        template_path: Path to the template image file
        button: Mouse button to click
        offset_x: X offset from center of found image
        offset_y: Y offset from center of found image
        timeout: If > 0, wait for image to appear (uses wait_for)
        interval: Time between checks when waiting
        threshold: Minimum confidence threshold (0.0-1.0)
        region: Optional region to search within (x, y, width, height)
        grayscale: Convert images to grayscale before matching
        method: OpenCV matching method

    Returns:
        MatchResult of the clicked image

    Raises:
        ImageNotFoundError: If image is not found
    """
    if timeout > 0:
        result = wait_for(
            template_path,
            timeout=timeout,
            interval=interval,
            threshold=threshold,
            region=region,
            grayscale=grayscale,
            method=method,
        )
    else:
        result = find_best(
            template_path,
            threshold=threshold,
            region=region,
            grayscale=grayscale,
            method=method,
        )
        if not result:
            raise ImageNotFoundError(template_path)

    # Click at center of found image with offset
    click_x = result.center[0] + offset_x
    click_y = result.center[1] + offset_y
    mouse.click_at(click_x, click_y, button=button)

    return result


def exists(
    template_path: str,
    threshold: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
    grayscale: bool = False,
    method: MatchMethod = DEFAULT_METHOD,
) -> bool:
    """
    Check if a template image exists on the screen.

    Args:
        template_path: Path to the template image file
        threshold: Minimum confidence threshold (0.0-1.0)
        region: Optional region to search within (x, y, width, height)
        grayscale: Convert images to grayscale before matching
        method: OpenCV matching method

    Returns:
        True if image is found, False otherwise
    """
    result = find_best(
        template_path,
        threshold=threshold,
        region=region,
        grayscale=grayscale,
        method=method,
    )
    return result is not None


def parse_method(method_str: str) -> MatchMethod:
    """Parse a method string into a MatchMethod enum."""
    method_map = {
        "ccoeff": MatchMethod.CCOEFF,
        "ccoeff_normed": MatchMethod.CCOEFF_NORMED,
        "ccorr": MatchMethod.CCORR,
        "ccorr_normed": MatchMethod.CCORR_NORMED,
        "sqdiff": MatchMethod.SQDIFF,
        "sqdiff_normed": MatchMethod.SQDIFF_NORMED,
    }
    key = method_str.lower().replace("-", "_")
    if key not in method_map:
        valid = ", ".join(method_map.keys())
        raise ValueError(f"Unknown method: {method_str}. Valid methods: {valid}")
    return method_map[key]
