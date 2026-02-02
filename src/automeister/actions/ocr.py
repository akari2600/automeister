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
