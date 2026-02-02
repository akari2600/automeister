"""OCR (Optical Character Recognition) actions using Tesseract."""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from automeister.actions import screen
from automeister.utils.process import check_command_exists, run_command


class OCRError(Exception):
    """Raised when OCR operations fail."""

    pass


@dataclass
class OCRResult:
    """Result of an OCR operation."""

    text: str
    confidence: float | None = None
    region: tuple[int, int, int, int] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "region": list(self.region) if self.region else None,
        }


@dataclass
class TextBounds:
    """Bounding box for found text."""

    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float | None = None

    @property
    def center(self) -> tuple[int, int]:
        """Get the center point of the bounds."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center_x": self.center[0],
            "center_y": self.center[1],
            "confidence": self.confidence,
        }


@dataclass
class WordBox:
    """A single word with its bounding box from OCR."""

    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float


def _get_tesseract_cmd() -> str:
    """Get the tesseract command."""
    if check_command_exists("tesseract"):
        return "tesseract"
    raise OCRError(
        "tesseract not found. Install with: sudo apt install tesseract-ocr"
    )


def ocr(
    image_path: str | None = None,
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
    psm: int = 3,
) -> OCRResult:
    """
    Perform OCR on a screen capture or image file.

    Args:
        image_path: Path to image file. If None, captures current screen.
        region: Screen region to capture (x, y, width, height).
        lang: Tesseract language code (e.g., 'eng', 'fra', 'deu').
        psm: Page segmentation mode (0-13). Default 3 = fully automatic.

    Returns:
        OCRResult with extracted text.

    Raises:
        OCRError: If OCR fails.
    """
    tesseract = _get_tesseract_cmd()

    # Capture screen if no image provided
    if image_path is None:
        image_path = screen.capture(region=region)
        cleanup_image = True
    else:
        cleanup_image = False

    try:
        # Run tesseract
        cmd = [
            tesseract,
            image_path,
            "stdout",
            "-l", lang,
            "--psm", str(psm),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise OCRError(f"Tesseract failed: {result.stderr}")

        text = result.stdout.strip()

        return OCRResult(
            text=text,
            region=region,
        )

    finally:
        # Clean up temp file if we created it
        if cleanup_image and image_path:
            try:
                Path(image_path).unlink(missing_ok=True)
            except Exception:
                pass


def ocr_with_confidence(
    image_path: str | None = None,
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
    psm: int = 3,
) -> OCRResult:
    """
    Perform OCR with confidence scores using TSV output.

    Args:
        image_path: Path to image file. If None, captures current screen.
        region: Screen region to capture (x, y, width, height).
        lang: Tesseract language code.
        psm: Page segmentation mode.

    Returns:
        OCRResult with extracted text and average confidence.
    """
    tesseract = _get_tesseract_cmd()

    # Capture screen if no image provided
    if image_path is None:
        image_path = screen.capture(region=region)
        cleanup_image = True
    else:
        cleanup_image = False

    try:
        # Run tesseract with TSV output for confidence
        cmd = [
            tesseract,
            image_path,
            "stdout",
            "-l", lang,
            "--psm", str(psm),
            "tsv",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise OCRError(f"Tesseract failed: {result.stderr}")

        # Parse TSV output
        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return OCRResult(text="", confidence=0.0, region=region)

        words = []
        confidences = []

        for line in lines[1:]:  # Skip header
            parts = line.split("\t")
            if len(parts) >= 12:
                conf = parts[10]  # confidence column
                text = parts[11]  # text column
                if text.strip() and conf != "-1":
                    words.append(text)
                    try:
                        confidences.append(float(conf))
                    except ValueError:
                        pass

        full_text = " ".join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            region=region,
        )

    finally:
        if cleanup_image and image_path:
            try:
                Path(image_path).unlink(missing_ok=True)
            except Exception:
                pass


def find_text(
    text: str,
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
    exact: bool = False,
    case_sensitive: bool = False,
) -> bool:
    """
    Check if text exists on screen.

    Args:
        text: Text to search for.
        region: Screen region to search.
        lang: Tesseract language code.
        exact: If True, requires exact match. If False, substring match.
        case_sensitive: If True, match is case-sensitive.

    Returns:
        True if text is found, False otherwise.
    """
    result = ocr(region=region, lang=lang)
    screen_text = result.text

    if not case_sensitive:
        screen_text = screen_text.lower()
        text = text.lower()

    if exact:
        # Check for exact word match
        words = screen_text.split()
        return text in words
    else:
        return text in screen_text


def wait_for_text(
    text: str,
    timeout: float = 30.0,
    interval: float = 1.0,
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
    exact: bool = False,
    case_sensitive: bool = False,
) -> OCRResult:
    """
    Wait for text to appear on screen.

    Args:
        text: Text to wait for.
        timeout: Maximum time to wait in seconds.
        interval: Time between checks in seconds.
        region: Screen region to search.
        lang: Tesseract language code.
        exact: If True, requires exact match.
        case_sensitive: If True, match is case-sensitive.

    Returns:
        OCRResult when text is found.

    Raises:
        OCRError: If timeout is reached.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = ocr(region=region, lang=lang)
        screen_text = result.text

        compare_screen = screen_text if case_sensitive else screen_text.lower()
        compare_text = text if case_sensitive else text.lower()

        found = False
        if exact:
            words = compare_screen.split()
            found = compare_text in words
        else:
            found = compare_text in compare_screen

        if found:
            return result

        time.sleep(interval)

    raise OCRError(f"Text '{text}' not found within {timeout} seconds")


def get_available_languages() -> list[str]:
    """
    Get list of available Tesseract languages.

    Returns:
        List of language codes.
    """
    tesseract = _get_tesseract_cmd()

    try:
        output = run_command([tesseract, "--list-langs"], timeout=10)
        lines = output.strip().split("\n")
        # Skip first line (header)
        return [lang.strip() for lang in lines[1:] if lang.strip()]
    except Exception:
        return ["eng"]  # Default fallback


def _get_word_boxes(
    image_path: str,
    lang: str = "eng",
    psm: int = 3,
) -> list[WordBox]:
    """
    Extract all words with their bounding boxes from an image.

    Args:
        image_path: Path to the image file.
        lang: Tesseract language code.
        psm: Page segmentation mode.

    Returns:
        List of WordBox objects with text and positions.
    """
    tesseract = _get_tesseract_cmd()

    cmd = [
        tesseract,
        image_path,
        "stdout",
        "-l", lang,
        "--psm", str(psm),
        "tsv",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise OCRError(f"Tesseract failed: {result.stderr}")

    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        return []

    word_boxes = []
    for line in lines[1:]:  # Skip header
        parts = line.split("\t")
        if len(parts) >= 12:
            text = parts[11].strip()
            conf_str = parts[10]

            # Skip empty text or invalid confidence
            if not text or conf_str == "-1":
                continue

            try:
                word_boxes.append(WordBox(
                    text=text,
                    left=int(parts[6]),
                    top=int(parts[7]),
                    width=int(parts[8]),
                    height=int(parts[9]),
                    confidence=float(conf_str),
                ))
            except (ValueError, IndexError):
                continue

    return word_boxes


def find_text_bounds(
    text: str,
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
    case_sensitive: bool = False,
) -> TextBounds | None:
    """
    Find text on screen and return its bounding box.

    This function searches for the exact text string (which may span multiple
    words) and returns the bounding box that encompasses all matched words.

    Args:
        text: Text string to search for (can contain spaces for multi-word search).
        region: Screen region to search within (x, y, width, height).
        lang: Tesseract language code.
        case_sensitive: If True, match is case-sensitive.

    Returns:
        TextBounds with position and dimensions if found, None otherwise.

    Example:
        # Find a row of buttons
        bounds = find_text_bounds(".deb x64 Arm32 Arm64")
        if bounds:
            print(f"Found at ({bounds.x}, {bounds.y})")

        # Then find specific text within those bounds
        arm64_bounds = find_text_bounds("Arm64", region=(bounds.x, bounds.y, bounds.width, bounds.height))
        if arm64_bounds:
            mouse.click_at(*arm64_bounds.center)
    """
    # Capture screen
    image_path = screen.capture(region=region)

    try:
        word_boxes = _get_word_boxes(image_path, lang=lang)

        if not word_boxes:
            return None

        # Normalize search text
        search_text = text if case_sensitive else text.lower()
        search_words = search_text.split()

        if not search_words:
            return None

        # Build a string of all OCR text to find the substring
        # Keep track of word positions in the concatenated string
        all_text_parts = []
        word_positions = []  # (start_idx, end_idx, word_box_idx)

        for i, wb in enumerate(word_boxes):
            start = len(" ".join(all_text_parts) + (" " if all_text_parts else ""))
            word_text = wb.text if case_sensitive else wb.text.lower()
            all_text_parts.append(word_text)
            end = len(" ".join(all_text_parts))
            word_positions.append((start, end, i))

        full_text = " ".join(all_text_parts)

        # Find the search text in the full OCR text
        search_start = full_text.find(search_text)
        if search_start == -1:
            return None

        search_end = search_start + len(search_text)

        # Find which word boxes are covered by this match
        matched_indices = []
        for start, end, idx in word_positions:
            # Check if this word overlaps with the search match
            if start < search_end and end > search_start:
                matched_indices.append(idx)

        if not matched_indices:
            return None

        # Calculate bounding box that encompasses all matched words
        matched_boxes = [word_boxes[i] for i in matched_indices]
        min_x = min(wb.left for wb in matched_boxes)
        min_y = min(wb.top for wb in matched_boxes)
        max_x = max(wb.left + wb.width for wb in matched_boxes)
        max_y = max(wb.top + wb.height for wb in matched_boxes)

        # Calculate average confidence
        avg_conf = sum(wb.confidence for wb in matched_boxes) / len(matched_boxes)

        # Adjust coordinates if we searched within a region
        if region:
            min_x += region[0]
            min_y += region[1]
            max_x += region[0]
            max_y += region[1]

        return TextBounds(
            text=text,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=avg_conf,
        )

    finally:
        Path(image_path).unlink(missing_ok=True)


def find_all_text_bounds(
    region: tuple[int, int, int, int] | None = None,
    lang: str = "eng",
) -> list[TextBounds]:
    """
    Get all words on screen with their bounding boxes.

    Useful for understanding UI layout and finding clickable elements.

    Args:
        region: Screen region to search within (x, y, width, height).
        lang: Tesseract language code.

    Returns:
        List of TextBounds for all detected words.
    """
    image_path = screen.capture(region=region)

    try:
        word_boxes = _get_word_boxes(image_path, lang=lang)

        results = []
        for wb in word_boxes:
            x = wb.left + (region[0] if region else 0)
            y = wb.top + (region[1] if region else 0)

            results.append(TextBounds(
                text=wb.text,
                x=x,
                y=y,
                width=wb.width,
                height=wb.height,
                confidence=wb.confidence,
            ))

        return results

    finally:
        Path(image_path).unlink(missing_ok=True)
