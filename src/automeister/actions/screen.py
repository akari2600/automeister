"""Screen capture actions."""

import os
from pathlib import Path

from automeister.config import get_config
from automeister.utils.process import run_command


def capture(
    region: tuple[int, int, int, int] | None = None,
    output: str | None = None,
    tool: str | None = None,
) -> str:
    """
    Capture the screen or a region of it.

    Args:
        region: Optional tuple of (x, y, width, height) for region capture
        output: Output file path. If None, generates a temp file.
        tool: Capture tool to use ("scrot" or "maim"). If None, uses config.

    Returns:
        Path to the captured image file.

    Raises:
        CommandNotFoundError: If the capture tool is not installed.
        CommandError: If the capture fails.
    """
    config = get_config()
    capture_tool = tool or config.capture.tool

    if output is None:
        output = f"/tmp/automeister_capture_{os.getpid()}.png"

    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if capture_tool == "scrot":
        cmd = _build_scrot_command(region, str(output_path))
    elif capture_tool == "maim":
        cmd = _build_maim_command(region, str(output_path))
    else:
        raise ValueError(f"Unknown capture tool: {capture_tool}")

    run_command(cmd, timeout=config.timeouts.screen_capture)
    return str(output_path)


def _build_scrot_command(
    region: tuple[int, int, int, int] | None,
    output: str,
) -> list[str]:
    """Build scrot command."""
    cmd = ["scrot"]

    if region:
        x, y, w, h = region
        # scrot uses -a for area selection: x,y,width,height
        cmd.extend(["-a", f"{x},{y},{w},{h}"])

    cmd.append(output)
    return cmd


def _build_maim_command(
    region: tuple[int, int, int, int] | None,
    output: str,
) -> list[str]:
    """Build maim command."""
    cmd = ["maim"]

    if region:
        x, y, w, h = region
        # maim uses -g for geometry: WxH+X+Y
        cmd.extend(["-g", f"{w}x{h}+{x}+{y}"])

    cmd.append(output)
    return cmd


def parse_region(region_str: str) -> tuple[int, int, int, int]:
    """
    Parse a region string into a tuple.

    Args:
        region_str: Region in format "x,y,w,h" or "x,y,width,height"

    Returns:
        Tuple of (x, y, width, height)

    Raises:
        ValueError: If the format is invalid
    """
    parts = region_str.split(",")
    if len(parts) != 4:
        raise ValueError(f"Invalid region format: {region_str}. Expected x,y,w,h")

    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
    except ValueError as e:
        raise ValueError(f"Invalid region values: {region_str}") from e
