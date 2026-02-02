"""CLI application for Automeister."""

import json
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from automeister import __version__
from automeister.actions import image, keyboard, mouse, ocr, screen, util, window
from automeister.macro import (
    MacroExecutor,
    find_macro,
    get_macros_dir,
    load_macro,
    load_macros,
)
from automeister.macro.executor import MacroExecutionError
from automeister.macro.parser import MacroParseError

# Main application
app = typer.Typer(
    name="automeister",
    help="Desktop automation tool for Linux X11 environments.",
    no_args_is_help=True,
)

# Exec subcommand group
exec_app = typer.Typer(
    name="exec",
    help="Execute automation actions directly.",
    no_args_is_help=True,
)
app.add_typer(exec_app, name="exec")

# Macro subcommand group
macro_app = typer.Typer(
    name="macro",
    help="Manage macros.",
    no_args_is_help=True,
)
app.add_typer(macro_app, name="macro")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"automeister {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = False,
) -> None:
    """Automeister - Desktop automation tool."""
    pass


@app.command("check")
def check_dependencies(
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
) -> None:
    """Check system dependencies and display their status."""
    from automeister.utils.process import check_command_exists

    dependencies = {
        "xdotool": {
            "required": True,
            "purpose": "Mouse and keyboard control",
            "install": "sudo apt install xdotool",
        },
        "scrot": {
            "required": False,
            "purpose": "Screen capture (primary)",
            "install": "sudo apt install scrot",
        },
        "maim": {
            "required": False,
            "purpose": "Screen capture (alternative)",
            "install": "sudo apt install maim",
        },
        "wmctrl": {
            "required": False,
            "purpose": "Window management",
            "install": "sudo apt install wmctrl",
        },
        "tesseract": {
            "required": False,
            "purpose": "OCR text recognition",
            "install": "sudo apt install tesseract-ocr",
        },
        "xclip": {
            "required": False,
            "purpose": "Clipboard operations",
            "install": "sudo apt install xclip",
        },
        "notify-send": {
            "required": False,
            "purpose": "Desktop notifications",
            "install": "sudo apt install libnotify-bin",
        },
    }

    results = []
    all_required_ok = True

    for cmd, info in dependencies.items():
        available = check_command_exists(cmd)
        results.append({
            "command": cmd,
            "available": available,
            "required": info["required"],
            "purpose": info["purpose"],
            "install": info["install"],
        })
        if info["required"] and not available:
            all_required_ok = False

    if json_output:
        typer.echo(json.dumps({
            "all_required_available": all_required_ok,
            "dependencies": results,
        }))
    else:
        typer.echo("Automeister Dependency Check")
        typer.echo("=" * 40)
        typer.echo("")

        for dep in results:
            status = "[OK]" if dep["available"] else "[MISSING]"
            req = " (required)" if dep["required"] else ""
            typer.echo(f"{status} {dep['command']}{req}")
            typer.echo(f"     Purpose: {dep['purpose']}")
            if not dep["available"]:
                typer.echo(f"     Install: {dep['install']}")
            typer.echo("")

        if all_required_ok:
            typer.echo("All required dependencies are available.")
        else:
            typer.echo("Some required dependencies are missing!")
            raise typer.Exit(1)


# =============================================================================
# Screen commands
# =============================================================================


@exec_app.command("screen.capture")
def screen_capture(
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Region to capture (x,y,w,h)"),
    ] = None,
    tool: Annotated[
        str | None,
        typer.Option("--tool", "-t", help="Capture tool (scrot or maim)"),
    ] = None,
) -> None:
    """Capture the screen or a region of it."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    result = screen.capture(region=region_tuple, output=output, tool=tool)
    typer.echo(f"Screenshot saved to: {result}")


# =============================================================================
# Image recognition commands
# =============================================================================


@exec_app.command("screen.find")
def screen_find(
    template: Annotated[str, typer.Argument(help="Path to template image")],
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Confidence threshold (0.0-1.0)"),
    ] = 0.8,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Search region (x,y,w,h)"),
    ] = None,
    grayscale: Annotated[
        bool,
        typer.Option("--grayscale", "-g", help="Use grayscale matching"),
    ] = False,
    method: Annotated[
        str,
        typer.Option("--method", "-m", help="Matching method"),
    ] = "ccoeff_normed",
    all_matches: Annotated[
        bool,
        typer.Option("--all", "-a", help="Return all matches"),
    ] = False,
) -> None:
    """Find a template image on the screen."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    match_method = image.parse_method(method)
    match_mode = "all" if all_matches else "best"

    matches = image.find(
        template,
        threshold=threshold,
        region=region_tuple,
        grayscale=grayscale,
        method=match_method,
        match_mode=match_mode,  # type: ignore
    )

    if not matches:
        typer.echo("No matches found")
        raise typer.Exit(1)

    for match in matches:
        typer.echo(
            f"Found at ({match.x}, {match.y}) "
            f"size {match.width}x{match.height} "
            f"confidence {match.confidence:.3f}"
        )


@exec_app.command("screen.wait-for")
def screen_wait_for(
    template: Annotated[str, typer.Argument(help="Path to template image")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-T", help="Timeout in seconds"),
    ] = 30.0,
    interval: Annotated[
        float,
        typer.Option("--interval", "-i", help="Check interval in seconds"),
    ] = 0.5,
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Confidence threshold (0.0-1.0)"),
    ] = 0.8,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Search region (x,y,w,h)"),
    ] = None,
    grayscale: Annotated[
        bool,
        typer.Option("--grayscale", "-g", help="Use grayscale matching"),
    ] = False,
    method: Annotated[
        str,
        typer.Option("--method", "-m", help="Matching method"),
    ] = "ccoeff_normed",
) -> None:
    """Wait for a template image to appear on screen."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    match_method = image.parse_method(method)

    try:
        match = image.wait_for(
            template,
            timeout=timeout,
            interval=interval,
            threshold=threshold,
            region=region_tuple,
            grayscale=grayscale,
            method=match_method,
        )
        typer.echo(
            f"Found at ({match.x}, {match.y}) "
            f"size {match.width}x{match.height} "
            f"confidence {match.confidence:.3f}"
        )
    except image.ImageNotFoundError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from None


@exec_app.command("screen.exists")
def screen_exists(
    template: Annotated[str, typer.Argument(help="Path to template image")],
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Confidence threshold (0.0-1.0)"),
    ] = 0.8,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Search region (x,y,w,h)"),
    ] = None,
    grayscale: Annotated[
        bool,
        typer.Option("--grayscale", "-g", help="Use grayscale matching"),
    ] = False,
) -> None:
    """Check if a template image exists on screen."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    found = image.exists(
        template,
        threshold=threshold,
        region=region_tuple,
        grayscale=grayscale,
    )

    if found:
        typer.echo("true")
    else:
        typer.echo("false")
        raise typer.Exit(1)


@exec_app.command("screen.ocr")
def screen_ocr(
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Screen region (x,y,w,h)"),
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="Tesseract language code"),
    ] = "eng",
    psm: Annotated[
        int,
        typer.Option("--psm", help="Page segmentation mode (0-13)"),
    ] = 3,
    image_path: Annotated[
        str | None,
        typer.Option("--image", "-i", help="Image file instead of screen capture"),
    ] = None,
) -> None:
    """Perform OCR on the screen or an image."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    try:
        result = ocr.ocr(
            image_path=image_path,
            region=region_tuple,
            lang=lang,
            psm=psm,
        )
        typer.echo(result.text)
    except ocr.OCRError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("screen.find-text")
def screen_find_text(
    text: Annotated[str, typer.Argument(help="Text to search for")],
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Screen region (x,y,w,h)"),
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="Tesseract language code"),
    ] = "eng",
    exact: Annotated[
        bool,
        typer.Option("--exact", "-e", help="Require exact word match"),
    ] = False,
    case_sensitive: Annotated[
        bool,
        typer.Option("--case-sensitive", "-c", help="Case-sensitive matching"),
    ] = False,
) -> None:
    """Check if text exists on screen using OCR."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    found = ocr.find_text(
        text,
        region=region_tuple,
        lang=lang,
        exact=exact,
        case_sensitive=case_sensitive,
    )

    if found:
        typer.echo("true")
    else:
        typer.echo("false")
        raise typer.Exit(1)


@exec_app.command("screen.wait-for-text")
def screen_wait_for_text(
    text: Annotated[str, typer.Argument(help="Text to wait for")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-T", help="Timeout in seconds"),
    ] = 30.0,
    interval: Annotated[
        float,
        typer.Option("--interval", "-i", help="Check interval in seconds"),
    ] = 1.0,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Screen region (x,y,w,h)"),
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", "-l", help="Tesseract language code"),
    ] = "eng",
    exact: Annotated[
        bool,
        typer.Option("--exact", "-e", help="Require exact word match"),
    ] = False,
    case_sensitive: Annotated[
        bool,
        typer.Option("--case-sensitive", "-c", help="Case-sensitive matching"),
    ] = False,
) -> None:
    """Wait for text to appear on screen using OCR."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    try:
        result = ocr.wait_for_text(
            text,
            timeout=timeout,
            interval=interval,
            region=region_tuple,
            lang=lang,
            exact=exact,
            case_sensitive=case_sensitive,
        )
        typer.echo(f"Found: {result.text[:100]}...")
    except ocr.OCRError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("mouse.click-image")
def mouse_click_image(
    template: Annotated[str, typer.Argument(help="Path to template image")],
    button: Annotated[
        str,
        typer.Option("--button", "-b", help="Button to click"),
    ] = "left",
    offset_x: Annotated[
        int,
        typer.Option("--offset-x", help="X offset from center"),
    ] = 0,
    offset_y: Annotated[
        int,
        typer.Option("--offset-y", help="Y offset from center"),
    ] = 0,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-T", help="Wait timeout (0 for no wait)"),
    ] = 0.0,
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Confidence threshold (0.0-1.0)"),
    ] = 0.8,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Search region (x,y,w,h)"),
    ] = None,
    grayscale: Annotated[
        bool,
        typer.Option("--grayscale", "-g", help="Use grayscale matching"),
    ] = False,
) -> None:
    """Find a template image and click on it."""
    region_tuple = None
    if region:
        region_tuple = screen.parse_region(region)

    try:
        match = image.click_image(
            template,
            button=button,  # type: ignore
            offset_x=offset_x,
            offset_y=offset_y,
            timeout=timeout,
            threshold=threshold,
            region=region_tuple,
            grayscale=grayscale,
        )
        typer.echo(f"Clicked at ({match.center[0]}, {match.center[1]})")
    except image.ImageNotFoundError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from None


# =============================================================================
# Mouse commands
# =============================================================================


@exec_app.command("mouse.move")
def mouse_move(
    x: Annotated[int, typer.Argument(help="X coordinate")],
    y: Annotated[int, typer.Argument(help="Y coordinate")],
    relative: Annotated[
        bool,
        typer.Option("--relative", "-r", help="Move relative to current position"),
    ] = False,
    duration: Annotated[
        float | None,
        typer.Option("--duration", "-d", help="Animation duration in seconds"),
    ] = None,
) -> None:
    """Move the mouse cursor."""
    mouse.move(x, y, relative=relative, duration=duration)
    typer.echo(f"Moved mouse to ({x}, {y})")


@exec_app.command("mouse.click")
def mouse_click(
    button: Annotated[
        str,
        typer.Option("--button", "-b", help="Button to click (left, middle, right)"),
    ] = "left",
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of clicks"),
    ] = 1,
) -> None:
    """Click the mouse button at current position."""
    mouse.click(button=button, count=count)  # type: ignore
    typer.echo(f"Clicked {button} button {count} time(s)")


@exec_app.command("mouse.click-at")
def mouse_click_at(
    x: Annotated[int, typer.Argument(help="X coordinate")],
    y: Annotated[int, typer.Argument(help="Y coordinate")],
    button: Annotated[
        str,
        typer.Option("--button", "-b", help="Button to click"),
    ] = "left",
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of clicks"),
    ] = 1,
) -> None:
    """Move to position and click."""
    mouse.click_at(x, y, button=button, count=count)  # type: ignore
    typer.echo(f"Clicked at ({x}, {y})")


@exec_app.command("mouse.drag")
def mouse_drag(
    x1: Annotated[int, typer.Argument(help="Start X coordinate")],
    y1: Annotated[int, typer.Argument(help="Start Y coordinate")],
    x2: Annotated[int, typer.Argument(help="End X coordinate")],
    y2: Annotated[int, typer.Argument(help="End Y coordinate")],
    button: Annotated[
        str,
        typer.Option("--button", "-b", help="Button to hold during drag"),
    ] = "left",
    duration: Annotated[
        float | None,
        typer.Option("--duration", "-d", help="Drag duration in seconds"),
    ] = None,
) -> None:
    """Drag from one position to another."""
    mouse.drag(x1, y1, x2, y2, button=button, duration=duration)  # type: ignore
    typer.echo(f"Dragged from ({x1}, {y1}) to ({x2}, {y2})")


@exec_app.command("mouse.scroll")
def mouse_scroll(
    amount: Annotated[int, typer.Argument(help="Scroll amount (positive=down, negative=up)")],
    horizontal: Annotated[
        bool,
        typer.Option("--horizontal", "-h", help="Scroll horizontally"),
    ] = False,
) -> None:
    """Scroll the mouse wheel."""
    mouse.scroll(amount, horizontal=horizontal)
    direction = "horizontally" if horizontal else "vertically"
    typer.echo(f"Scrolled {amount} units {direction}")


@exec_app.command("mouse.position")
def mouse_position() -> None:
    """Get current mouse position."""
    x, y = mouse.get_position()
    typer.echo(f"{x},{y}")


# =============================================================================
# Keyboard commands
# =============================================================================


@exec_app.command("keyboard.type")
def keyboard_type(
    text: Annotated[str, typer.Argument(help="Text to type")],
    delay: Annotated[
        int | None,
        typer.Option("--delay", "-d", help="Delay between keystrokes in milliseconds"),
    ] = None,
) -> None:
    """Type text using the keyboard."""
    keyboard.type_text(text, delay=delay)
    typer.echo(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")


@exec_app.command("keyboard.key")
def keyboard_key(
    key_name: Annotated[str, typer.Argument(help="Key to press (e.g., Return, Tab, a, F1)")],
    modifiers: Annotated[
        str | None,
        typer.Option("--modifiers", "-m", help="Comma-separated modifiers (e.g., ctrl,shift)"),
    ] = None,
) -> None:
    """Press a single key, optionally with modifiers."""
    mod_list = modifiers.split(",") if modifiers else None
    normalized_key = keyboard.normalize_key(key_name)
    keyboard.key(normalized_key, modifiers=mod_list)
    if mod_list:
        typer.echo(f"Pressed: {'+'.join(mod_list)}+{key_name}")
    else:
        typer.echo(f"Pressed: {key_name}")


@exec_app.command("keyboard.hotkey")
def keyboard_hotkey(
    combo: Annotated[str, typer.Argument(help="Key combination (e.g., ctrl+c, alt+F4)")],
) -> None:
    """Press a key combination."""
    keyboard.hotkey(combo)
    typer.echo(f"Pressed: {combo}")


# =============================================================================
# Utility commands
# =============================================================================


@exec_app.command("delay")
def delay_cmd(
    seconds: Annotated[float, typer.Argument(help="Seconds to wait")],
) -> None:
    """Wait for a specified amount of time."""
    util.delay(seconds)
    typer.echo(f"Waited {seconds} seconds")


@exec_app.command("notify")
def notify_cmd(
    message: Annotated[str, typer.Argument(help="Notification message")],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Notification title"),
    ] = None,
    urgency: Annotated[
        str | None,
        typer.Option("--urgency", "-u", help="Urgency level (low, normal, critical)"),
    ] = None,
    timeout: Annotated[
        int | None,
        typer.Option("--timeout", help="Display duration in milliseconds"),
    ] = None,
) -> None:
    """Show a desktop notification."""
    util.notify(message, title=title, urgency=urgency, timeout=timeout)
    typer.echo("Notification sent")


@exec_app.command("clipboard.get")
def clipboard_get_cmd() -> None:
    """Get the current clipboard content."""
    content = util.clipboard_get()
    typer.echo(content)


@exec_app.command("clipboard.set")
def clipboard_set_cmd(
    text: Annotated[str, typer.Argument(help="Text to copy to clipboard")],
) -> None:
    """Set the clipboard content."""
    util.clipboard_set(text)
    typer.echo("Text copied to clipboard")


@exec_app.command("shell")
def shell_cmd(
    command: Annotated[str, typer.Argument(help="Shell command to execute")],
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", "-t", help="Timeout in seconds"),
    ] = None,
) -> None:
    """Run an arbitrary shell command."""
    output = util.shell(command, timeout=timeout)
    if output:
        typer.echo(output)


@exec_app.command("log")
def log_cmd(
    message: Annotated[str, typer.Argument(help="Message to log")],
    level: Annotated[
        str,
        typer.Option("--level", "-l", help="Log level (debug, info, warn, error)"),
    ] = "info",
) -> None:
    """Print a log message."""
    prefix = {"debug": "[DEBUG]", "info": "[INFO]", "warn": "[WARN]", "error": "[ERROR]"}.get(
        level, "[INFO]"
    )
    typer.echo(f"{prefix} {message}")


@exec_app.command("fail")
def fail_cmd(
    message: Annotated[str, typer.Argument(help="Error message")] = "Execution failed",
) -> None:
    """Exit with an error."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


# =============================================================================
# Window commands
# =============================================================================


@exec_app.command("window.list")
def window_list(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Filter by window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="Filter by WM_CLASS"),
    ] = None,
    desktop: Annotated[
        int | None,
        typer.Option("--desktop", "-d", help="Filter by desktop number"),
    ] = None,
) -> None:
    """List all windows."""
    try:
        windows = window.list_windows(title=title, wm_class=wm_class, desktop=desktop)
        for win in windows:
            typer.echo(f"{win.window_id}  {win.title[:50]:<50}  {win.wm_class}")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.focus")
def window_focus(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Focus a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        win = window.focus(title=title, wm_class=wm_class, window_id=window_id)
        typer.echo(f"Focused: {win.title}")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.move")
def window_move(
    x: Annotated[int, typer.Argument(help="X coordinate")],
    y: Annotated[int, typer.Argument(help="Y coordinate")],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Move a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        win = window.move(x, y, title=title, wm_class=wm_class, window_id=window_id)
        typer.echo(f"Moved: {win.title} to ({x}, {y})")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.resize")
def window_resize(
    width: Annotated[int, typer.Argument(help="Width")],
    height: Annotated[int, typer.Argument(help="Height")],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Resize a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        win = window.resize(width, height, title=title, wm_class=wm_class, window_id=window_id)
        typer.echo(f"Resized: {win.title} to {width}x{height}")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.minimize")
def window_minimize(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Minimize a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        window.minimize(title=title, wm_class=wm_class, window_id=window_id)
        typer.echo("Window minimized")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.maximize")
def window_maximize(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Maximize a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        window.maximize(title=title, wm_class=wm_class, window_id=window_id)
        typer.echo("Window maximized")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.restore")
def window_restore(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Restore (unmaximize) a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        window.unmaximize(title=title, wm_class=wm_class, window_id=window_id)
        typer.echo("Window restored")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.close")
def window_close(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS"),
    ] = None,
    window_id: Annotated[
        str | None,
        typer.Option("--id", "-i", help="Window ID (hex)"),
    ] = None,
) -> None:
    """Close a window."""
    if not any([title, wm_class, window_id]):
        typer.echo("Error: Must specify --title, --class, or --id", err=True)
        raise typer.Exit(1)

    try:
        window.close(title=title, wm_class=wm_class, window_id=window_id)
        typer.echo("Window closed")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


@exec_app.command("window.wait-for")
def window_wait_for(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Window title to wait for"),
    ] = None,
    wm_class: Annotated[
        str | None,
        typer.Option("--class", "-c", help="WM_CLASS to wait for"),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-T", help="Timeout in seconds"),
    ] = 30.0,
    interval: Annotated[
        float,
        typer.Option("--interval", "-i", help="Check interval in seconds"),
    ] = 0.5,
) -> None:
    """Wait for a window to appear."""
    if not any([title, wm_class]):
        typer.echo("Error: Must specify --title or --class", err=True)
        raise typer.Exit(1)

    try:
        win = window.wait_for(title=title, wm_class=wm_class, timeout=timeout, interval=interval)
        typer.echo(f"Found: {win.window_id}  {win.title}")
    except window.WindowError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None


# =============================================================================
# Macro commands
# =============================================================================


@app.command("run")
def run_macro(
    macro_name: Annotated[str, typer.Argument(help="Name or path to macro")],
    params: Annotated[
        list[str] | None,
        typer.Option("--param", "-p", help="Parameter in key=value format"),
    ] = None,
    params_file: Annotated[
        str | None,
        typer.Option("--params-file", "-f", help="JSON file with parameters"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show execution details"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
) -> None:
    """Run a macro by name or file path."""
    import time

    start_time = time.time()

    # Parse parameters
    param_dict: dict[str, str] = {}

    if params_file:
        with open(params_file) as f:
            param_dict.update(json.load(f))

    if params:
        for param in params:
            if "=" not in param:
                if json_output:
                    typer.echo(json.dumps({
                        "success": False,
                        "error": f"Invalid parameter format: {param} (expected key=value)",
                    }))
                else:
                    typer.echo(f"Invalid parameter format: {param} (expected key=value)")
                raise typer.Exit(1)
            key, value = param.split("=", 1)
            param_dict[key] = value

    # Load macro
    try:
        # Check if it's a file path
        if macro_name.endswith((".yaml", ".yml")) or "/" in macro_name:
            macro = load_macro(macro_name)
        else:
            macro = find_macro(macro_name)
            if macro is None:
                if json_output:
                    typer.echo(json.dumps({
                        "success": False,
                        "error": f"Macro not found: {macro_name}",
                    }))
                else:
                    typer.echo(f"Macro not found: {macro_name}")
                raise typer.Exit(1)
    except FileNotFoundError as e:
        if json_output:
            typer.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            typer.echo(str(e))
        raise typer.Exit(1) from None
    except MacroParseError as e:
        if json_output:
            typer.echo(json.dumps({"success": False, "error": f"Parse error: {e}"}))
        else:
            typer.echo(f"Error parsing macro: {e}")
        raise typer.Exit(1) from None

    # Execute macro
    executor = MacroExecutor(verbose=verbose)
    try:
        executor.execute(macro, params=param_dict)
        elapsed = time.time() - start_time
        if json_output:
            typer.echo(json.dumps({
                "success": True,
                "macro": macro.name,
                "elapsed_seconds": round(elapsed, 3),
            }))
        else:
            typer.echo(f"Macro '{macro.name}' completed successfully")
    except MacroExecutionError as e:
        elapsed = time.time() - start_time
        if json_output:
            typer.echo(json.dumps({
                "success": False,
                "macro": macro.name,
                "error": str(e),
                "elapsed_seconds": round(elapsed, 3),
            }))
        else:
            typer.echo(f"Execution failed: {e}")
        raise typer.Exit(1) from None


@app.command("debug")
def debug_macro(
    macro_name: Annotated[str, typer.Argument(help="Name or path to macro")],
    params: Annotated[
        list[str] | None,
        typer.Option("--param", "-p", help="Parameter in key=value format"),
    ] = None,
    step: Annotated[
        bool,
        typer.Option("--step", "-s", help="Pause before each action"),
    ] = False,
) -> None:
    """Debug a macro with verbose output and optional stepping."""
    # Parse parameters
    param_dict: dict[str, str] = {}
    if params:
        for param in params:
            if "=" not in param:
                typer.echo(f"Invalid parameter format: {param} (expected key=value)")
                raise typer.Exit(1)
            key, value = param.split("=", 1)
            param_dict[key] = value

    # Load macro
    try:
        if macro_name.endswith((".yaml", ".yml")) or "/" in macro_name:
            macro = load_macro(macro_name)
        else:
            macro = find_macro(macro_name)
            if macro is None:
                typer.echo(f"Macro not found: {macro_name}")
                raise typer.Exit(1)
    except (FileNotFoundError, MacroParseError) as e:
        typer.echo(str(e))
        raise typer.Exit(1) from None

    typer.echo(f"=== Debugging: {macro.name} ===")
    typer.echo(f"File: {macro.file_path}")
    typer.echo(f"Actions: {len(macro.actions)}")
    typer.echo(f"Parameters: {param_dict}")
    typer.echo("")

    # Create a custom executor for debugging
    from automeister.macro.context import MacroContext
    from automeister.macro.executor import ACTION_HANDLERS, LoopBreak, LoopContinue

    validated_params = macro.validate_params(param_dict)
    context = MacroContext(params=validated_params, vars=macro.vars)

    for i, action in enumerate(macro.actions):
        typer.echo(f"[{i + 1}/{len(macro.actions)}] {action.action}")
        if action.args:
            for key, value in action.args.items():
                if key not in ("then", "else", "actions", "catch", "finally"):
                    typer.echo(f"       {key}: {value}")

        if step:
            response = typer.prompt("Press Enter to execute (or 'q' to quit)", default="")
            if response.lower() == "q":
                typer.echo("Debug session aborted")
                raise typer.Exit(0)

        # Check condition
        if action.condition:
            is_met = context.evaluate_condition(action.condition)
            typer.echo(f"       Condition '{action.condition}' = {is_met}")
            if not is_met:
                typer.echo("       SKIPPED (condition not met)")
                continue

        # Execute
        handler = ACTION_HANDLERS.get(action.action)
        if handler is None:
            typer.echo(f"       ERROR: Unknown action '{action.action}'")
            raise typer.Exit(1)

        try:
            # Render args
            rendered_args: dict = {}
            for key, value in action.args.items():
                if key in ("then", "else", "actions", "catch", "finally"):
                    rendered_args[key] = value
                else:
                    rendered_args[key] = context.render_value(value)

            # Create a dummy executor for the handler
            dummy_executor = MacroExecutor(verbose=True)
            result = handler(rendered_args, context, dummy_executor)

            if result is not None:
                typer.echo(f"       Result: {result}")
            typer.echo("       OK")
        except (LoopBreak, LoopContinue) as e:
            typer.echo(f"       Loop control: {type(e).__name__}")
        except Exception as e:
            typer.echo(f"       ERROR: {e}")
            raise typer.Exit(1) from None

        # Show variable changes
        if context._runtime_vars:
            typer.echo(f"       Variables: {context._runtime_vars}")

        typer.echo("")

    typer.echo("=== Debug complete ===")


@macro_app.command("list")
def macro_list(
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
) -> None:
    """List all available macros."""
    macros_dir = get_macros_dir()

    if not macros_dir.exists():
        if json_output:
            typer.echo(json.dumps({"macros": [], "error": f"No macros directory: {macros_dir}"}))
        else:
            typer.echo(f"No macros directory found at {macros_dir}")
            typer.echo("Create it with: mkdir -p ~/.config/automeister/macros")
        return

    macros = load_macros()

    if json_output:
        macro_list_data = [
            {
                "name": name,
                "description": macro.description,
                "parameters": len(macro.parameters),
                "actions": len(macro.actions),
                "file_path": macro.file_path,
            }
            for name, macro in sorted(macros.items())
        ]
        typer.echo(json.dumps({"macros": macro_list_data}))
        return

    if not macros:
        typer.echo("No macros found")
        return

    for name, macro in sorted(macros.items()):
        desc = f" - {macro.description}" if macro.description else ""
        typer.echo(f"  {name}{desc}")


@macro_app.command("show")
def macro_show(
    macro_name: Annotated[str, typer.Argument(help="Name or path to macro")],
) -> None:
    """Show details of a macro."""
    try:
        if macro_name.endswith((".yaml", ".yml")) or "/" in macro_name:
            macro = load_macro(macro_name)
        else:
            macro = find_macro(macro_name)
            if macro is None:
                typer.echo(f"Macro not found: {macro_name}")
                raise typer.Exit(1)
    except (FileNotFoundError, MacroParseError) as e:
        typer.echo(str(e))
        raise typer.Exit(1) from None

    typer.echo(f"Name: {macro.name}")
    if macro.description:
        typer.echo(f"Description: {macro.description}")
    if macro.file_path:
        typer.echo(f"File: {macro.file_path}")

    if macro.parameters:
        typer.echo("\nParameters:")
        for param in macro.parameters:
            req = "required" if param.required else f"default={param.default}"
            typer.echo(f"  {param.name} ({param.type}, {req})")
            if param.description:
                typer.echo(f"    {param.description}")

    if macro.vars:
        typer.echo("\nVariables:")
        for name, value in macro.vars.items():
            typer.echo(f"  {name} = {value}")

    typer.echo(f"\nActions: {len(macro.actions)}")
    for i, action in enumerate(macro.actions):
        name = f" [{action.name}]" if action.name else ""
        cond = f" (if: {action.condition})" if action.condition else ""
        typer.echo(f"  {i + 1}. {action.action}{name}{cond}")


@macro_app.command("validate")
def macro_validate(
    macro_name: Annotated[str, typer.Argument(help="Name or path to macro")],
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output results as JSON"),
    ] = False,
) -> None:
    """Validate a macro's syntax and structure."""
    from automeister.macro.executor import ACTION_HANDLERS

    errors: list[str] = []
    warnings: list[str] = []

    # Try to load the macro
    try:
        if macro_name.endswith((".yaml", ".yml")) or "/" in macro_name:
            macro = load_macro(macro_name)
        else:
            macro = find_macro(macro_name)
            if macro is None:
                if json_output:
                    typer.echo(json.dumps({
                        "valid": False,
                        "errors": [f"Macro not found: {macro_name}"],
                        "warnings": [],
                    }))
                else:
                    typer.echo(f"Error: Macro not found: {macro_name}")
                raise typer.Exit(1)
    except (FileNotFoundError, MacroParseError) as e:
        if json_output:
            typer.echo(json.dumps({
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
            }))
        else:
            typer.echo(f"Error: {e}")
        raise typer.Exit(1) from None

    # Validate actions
    for i, action in enumerate(macro.actions):
        action_name = action.action
        if action_name not in ACTION_HANDLERS:
            errors.append(f"Action {i + 1}: Unknown action '{action_name}'")

    # Validate parameters
    for param in macro.parameters:
        if param.type not in ("string", "integer", "float", "boolean", "list"):
            warnings.append(
                f"Parameter '{param.name}': Unknown type '{param.type}', defaulting to string"
            )

    # Check for empty actions list
    if not macro.actions:
        warnings.append("Macro has no actions defined")

    # Output results
    is_valid = len(errors) == 0

    if json_output:
        typer.echo(json.dumps({
            "valid": is_valid,
            "macro": macro.name,
            "file_path": macro.file_path,
            "actions_count": len(macro.actions),
            "parameters_count": len(macro.parameters),
            "errors": errors,
            "warnings": warnings,
        }))
    else:
        if is_valid:
            typer.echo(f"Macro '{macro.name}' is valid")
            typer.echo(f"  Actions: {len(macro.actions)}")
            typer.echo(f"  Parameters: {len(macro.parameters)}")
        else:
            typer.echo(f"Macro '{macro.name}' has errors:")
            for error in errors:
                typer.echo(f"  ERROR: {error}")

        for warning in warnings:
            typer.echo(f"  WARNING: {warning}")

    if not is_valid:
        raise typer.Exit(1)


@macro_app.command("create")
def macro_create(
    name: Annotated[str, typer.Argument(help="Name for the new macro")],
) -> None:
    """Create a new macro from a template."""
    macros_dir = get_macros_dir()
    macros_dir.mkdir(parents=True, exist_ok=True)

    file_path = macros_dir / f"{name}.yaml"

    if file_path.exists():
        typer.echo(f"Macro already exists: {file_path}")
        raise typer.Exit(1)

    template = f'''name: {name}
description: ""

# Optional parameters
# parameters:
#   - name: param1
#     type: string
#     required: true
#     description: "Description of param1"

# Optional variables
# vars:
#   my_var: "value"

actions:
  - action: delay
    seconds: 1

  # Add more actions here
'''

    file_path.write_text(template)
    typer.echo(f"Created macro: {file_path}")
    typer.echo("Edit the file to customize your macro")


@macro_app.command("edit")
def macro_edit(
    macro_name: Annotated[str, typer.Argument(help="Name of macro to edit")],
) -> None:
    """Open a macro in the default editor."""
    macro = find_macro(macro_name)
    if macro is None or macro.file_path is None:
        # Try as direct path
        macros_dir = get_macros_dir()
        for ext in (".yaml", ".yml"):
            path = macros_dir / f"{macro_name}{ext}"
            if path.exists():
                file_path = str(path)
                break
        else:
            typer.echo(f"Macro not found: {macro_name}")
            raise typer.Exit(1)
    else:
        file_path = macro.file_path

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, file_path])


@macro_app.command("delete")
def macro_delete(
    macro_name: Annotated[str, typer.Argument(help="Name of macro to delete")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a macro."""
    macro = find_macro(macro_name)
    if macro is None or macro.file_path is None:
        typer.echo(f"Macro not found: {macro_name}")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete macro '{macro_name}'?")
        if not confirm:
            typer.echo("Cancelled")
            return

    Path(macro.file_path).unlink()
    typer.echo(f"Deleted: {macro.file_path}")


if __name__ == "__main__":
    app()
