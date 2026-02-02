"""MCP Server for Automeister - exposes desktop automation tools for Claude Code."""

import base64
from pathlib import Path
from typing import Any

from mcp.server import FastMCP

from automeister.actions import image, keyboard, mouse, ocr, screen, window
from automeister.macro.executor import MacroExecutor
from automeister.macro.parser import find_macro

# Create the MCP server
mcp = FastMCP(name="automeister")


# =============================================================================
# Screen Tools
# =============================================================================


@mcp.tool()
def screen_capture(
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Capture the screen or a region of it.

    Returns the screenshot as a base64-encoded PNG for multimodal analysis,
    or saves to a file if output_path is specified.

    Args:
        region_x: X coordinate of region to capture (optional)
        region_y: Y coordinate of region to capture (optional)
        region_width: Width of region to capture (optional)
        region_height: Height of region to capture (optional)
        output_path: Path to save the screenshot (optional, returns base64 if not specified)

    Returns:
        Dictionary with 'path' and optionally 'base64' image data
    """
    region = None
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = (region_x, region_y, region_width, region_height)

    screenshot_path = screen.capture(region=region, output=output_path)

    result: dict[str, Any] = {"path": screenshot_path}

    # If no output path specified, return base64 for multimodal analysis
    if output_path is None:
        with open(screenshot_path, "rb") as f:
            result["base64"] = base64.b64encode(f.read()).decode("utf-8")
        result["mime_type"] = "image/png"
        # Clean up temp file
        Path(screenshot_path).unlink(missing_ok=True)

    return result


@mcp.tool()
def screen_find(
    template_path: str,
    threshold: float = 0.8,
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    grayscale: bool = False,
) -> dict[str, Any]:
    """
    Find a template image on the screen using OpenCV template matching.

    Args:
        template_path: Path to the template image file to search for
        threshold: Minimum confidence threshold (0.0-1.0), default 0.8
        region_x: X coordinate of search region (optional)
        region_y: Y coordinate of search region (optional)
        region_width: Width of search region (optional)
        region_height: Height of search region (optional)
        grayscale: Convert images to grayscale before matching

    Returns:
        Dictionary with match info (x, y, width, height, confidence, center_x, center_y)
        or {'found': False} if not found
    """
    region = None
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = (region_x, region_y, region_width, region_height)

    result = image.find_best(
        template_path,
        threshold=threshold,
        region=region,
        grayscale=grayscale,
    )

    if result:
        return {
            "found": True,
            **result.to_dict(),
        }
    return {"found": False}


@mcp.tool()
def screen_ocr(
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    lang: str = "eng",
) -> dict[str, Any]:
    """
    Extract text from the screen using OCR (Tesseract).

    Args:
        region_x: X coordinate of region to OCR (optional)
        region_y: Y coordinate of region to OCR (optional)
        region_width: Width of region to OCR (optional)
        region_height: Height of region to OCR (optional)
        lang: Tesseract language code (default: 'eng')

    Returns:
        Dictionary with 'text' and optional 'confidence' score
    """
    region = None
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = (region_x, region_y, region_width, region_height)

    result = ocr.ocr(region=region, lang=lang)
    return result.to_dict()


@mcp.tool()
def screen_wait_for_text(
    text: str,
    timeout: float = 30.0,
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    exact: bool = False,
) -> dict[str, Any]:
    """
    Wait for text to appear on screen via OCR.

    Args:
        text: Text to wait for
        timeout: Maximum time to wait in seconds (default: 30)
        region_x: X coordinate of search region (optional)
        region_y: Y coordinate of search region (optional)
        region_width: Width of search region (optional)
        region_height: Height of search region (optional)
        exact: If True, require exact word match; if False, substring match

    Returns:
        Dictionary with 'found': True and OCR result if found,
        or raises OCRError on timeout
    """
    region = None
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = (region_x, region_y, region_width, region_height)

    result = ocr.wait_for_text(
        text,
        timeout=timeout,
        region=region,
        exact=exact,
    )
    return {"found": True, **result.to_dict()}


# =============================================================================
# Mouse Tools
# =============================================================================


@mcp.tool()
def mouse_move(
    x: int,
    y: int,
    relative: bool = False,
    duration: float | None = None,
) -> dict[str, str]:
    """
    Move the mouse cursor to a position.

    Args:
        x: X coordinate (absolute) or delta (if relative)
        y: Y coordinate (absolute) or delta (if relative)
        relative: If True, move relative to current position
        duration: Animation duration in seconds (0 for instant)

    Returns:
        Dictionary with 'status': 'ok'
    """
    mouse.move(x, y, relative=relative, duration=duration)
    return {"status": "ok"}


@mcp.tool()
def mouse_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    count: int = 1,
) -> dict[str, str]:
    """
    Click the mouse at current position or specified coordinates.

    Args:
        x: X coordinate to click at (optional, uses current position if not specified)
        y: Y coordinate to click at (optional, uses current position if not specified)
        button: Button to click ('left', 'middle', 'right')
        count: Number of clicks (1 for single, 2 for double, etc.)

    Returns:
        Dictionary with 'status': 'ok'
    """
    if x is not None and y is not None:
        mouse.click_at(x, y, button=button, count=count)  # type: ignore
    else:
        mouse.click(button=button, count=count)  # type: ignore
    return {"status": "ok"}


@mcp.tool()
def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.5,
) -> dict[str, str]:
    """
    Drag the mouse from one position to another.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        button: Button to hold during drag ('left', 'middle', 'right')
        duration: Duration of the drag in seconds

    Returns:
        Dictionary with 'status': 'ok'
    """
    mouse.drag(start_x, start_y, end_x, end_y, button=button, duration=duration)  # type: ignore
    return {"status": "ok"}


@mcp.tool()
def mouse_scroll(
    amount: int,
    horizontal: bool = False,
) -> dict[str, str]:
    """
    Scroll the mouse wheel.

    Args:
        amount: Scroll amount (positive = down/right, negative = up/left)
        horizontal: If True, scroll horizontally

    Returns:
        Dictionary with 'status': 'ok'
    """
    mouse.scroll(amount, horizontal=horizontal)
    return {"status": "ok"}


# =============================================================================
# Keyboard Tools
# =============================================================================


@mcp.tool()
def keyboard_type(
    text: str,
    delay: int | None = None,
) -> dict[str, str]:
    """
    Type text using the keyboard.

    Args:
        text: Text to type
        delay: Delay between keystrokes in milliseconds (optional)

    Returns:
        Dictionary with 'status': 'ok'
    """
    keyboard.type_text(text, delay=delay)
    return {"status": "ok"}


@mcp.tool()
def keyboard_key(
    key: str,
    modifiers: list[str] | None = None,
) -> dict[str, str]:
    """
    Press a single key, optionally with modifiers.

    Args:
        key: Key name (e.g., 'Return', 'Tab', 'a', 'F1', 'Escape')
        modifiers: List of modifiers (e.g., ['ctrl'], ['ctrl', 'shift'])

    Returns:
        Dictionary with 'status': 'ok'
    """
    keyboard.key(key, modifiers=modifiers)
    return {"status": "ok"}


@mcp.tool()
def keyboard_hotkey(
    combo: str,
) -> dict[str, str]:
    """
    Press a key combination.

    Args:
        combo: Key combination string (e.g., 'ctrl+c', 'ctrl+shift+s', 'alt+F4')

    Returns:
        Dictionary with 'status': 'ok'
    """
    keyboard.hotkey(combo)
    return {"status": "ok"}


# =============================================================================
# Window Tools
# =============================================================================


@mcp.tool()
def window_list(
    title_filter: str | None = None,
    wm_class_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    List all windows, optionally filtered.

    Args:
        title_filter: Filter by window title (substring match, case-insensitive)
        wm_class_filter: Filter by WM_CLASS (substring match, case-insensitive)

    Returns:
        List of window info dictionaries with id, title, wm_class, x, y, width, height
    """
    windows = window.list_windows(title=title_filter, wm_class=wm_class_filter)
    return [w.to_dict() for w in windows]


@mcp.tool()
def window_focus(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, Any]:
    """
    Focus a window (bring to front and activate).

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        title: Window title to focus
        wm_class: WM_CLASS to focus
        window_id: Window ID (hex format, e.g., '0x12345678')

    Returns:
        Window info dictionary of the focused window
    """
    result = window.focus(title=title, wm_class=wm_class, window_id=window_id)
    return result.to_dict()


@mcp.tool()
def window_move(
    x: int,
    y: int,
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, Any]:
    """
    Move a window to a position.

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        x: Target X coordinate
        y: Target Y coordinate
        title: Window title
        wm_class: WM_CLASS
        window_id: Window ID (hex format)

    Returns:
        Window info dictionary of the moved window
    """
    result = window.move(x, y, title=title, wm_class=wm_class, window_id=window_id)
    return result.to_dict()


@mcp.tool()
def window_resize(
    width: int,
    height: int,
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, Any]:
    """
    Resize a window.

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        width: Target width
        height: Target height
        title: Window title
        wm_class: WM_CLASS
        window_id: Window ID (hex format)

    Returns:
        Window info dictionary of the resized window
    """
    result = window.resize(width, height, title=title, wm_class=wm_class, window_id=window_id)
    return result.to_dict()


@mcp.tool()
def window_minimize(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, str]:
    """
    Minimize a window.

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        title: Window title
        wm_class: WM_CLASS
        window_id: Window ID (hex format)

    Returns:
        Dictionary with 'status': 'ok'
    """
    window.minimize(title=title, wm_class=wm_class, window_id=window_id)
    return {"status": "ok"}


@mcp.tool()
def window_maximize(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, str]:
    """
    Maximize a window.

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        title: Window title
        wm_class: WM_CLASS
        window_id: Window ID (hex format)

    Returns:
        Dictionary with 'status': 'ok'
    """
    window.maximize(title=title, wm_class=wm_class, window_id=window_id)
    return {"status": "ok"}


@mcp.tool()
def window_close(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> dict[str, str]:
    """
    Close a window gracefully.

    Must specify at least one of: title, wm_class, or window_id.

    Args:
        title: Window title
        wm_class: WM_CLASS
        window_id: Window ID (hex format)

    Returns:
        Dictionary with 'status': 'ok'
    """
    window.close(title=title, wm_class=wm_class, window_id=window_id)
    return {"status": "ok"}


# =============================================================================
# Macro Tools
# =============================================================================


@mcp.tool()
def run_macro(
    name: str,
    params: dict[str, Any] | None = None,
    verbose: bool = False,
) -> dict[str, str]:
    """
    Execute an Automeister macro by name.

    Macros are YAML files that define sequences of automation actions.
    Look for macros in ~/.config/automeister/macros/ or the current directory.

    Args:
        name: Name of the macro to run (without .yaml extension)
        params: Optional parameters to pass to the macro
        verbose: If True, print action details during execution

    Returns:
        Dictionary with 'status': 'ok' on success
    """
    macro = find_macro(name)
    if macro is None:
        raise ValueError(f"Macro not found: {name}")

    executor = MacroExecutor(verbose=verbose)
    executor.execute(macro, params or {})
    return {"status": "ok"}


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
def delay(seconds: float) -> dict[str, str]:
    """
    Pause execution for a specified duration.

    Args:
        seconds: Number of seconds to wait

    Returns:
        Dictionary with 'status': 'ok'
    """
    import time

    time.sleep(seconds)
    return {"status": "ok"}


# =============================================================================
# Server Entry Point
# =============================================================================


def main() -> None:
    """Run the MCP server via stdio transport."""
    import asyncio

    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
