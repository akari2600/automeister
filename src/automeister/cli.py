"""CLI application for Automeister."""

import json
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from automeister import __version__
from automeister.actions import image, keyboard, mouse, screen, util
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
) -> None:
    """Run a macro by name or file path."""
    # Parse parameters
    param_dict: dict[str, str] = {}

    if params_file:
        with open(params_file) as f:
            param_dict.update(json.load(f))

    if params:
        for param in params:
            if "=" not in param:
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
                typer.echo(f"Macro not found: {macro_name}")
                raise typer.Exit(1)
    except FileNotFoundError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from None
    except MacroParseError as e:
        typer.echo(f"Error parsing macro: {e}")
        raise typer.Exit(1) from None

    # Execute macro
    executor = MacroExecutor(verbose=verbose)
    try:
        executor.execute(macro, params=param_dict)
        typer.echo(f"Macro '{macro.name}' completed successfully")
    except MacroExecutionError as e:
        typer.echo(f"Execution failed: {e}")
        raise typer.Exit(1) from None


@macro_app.command("list")
def macro_list() -> None:
    """List all available macros."""
    macros_dir = get_macros_dir()

    if not macros_dir.exists():
        typer.echo(f"No macros directory found at {macros_dir}")
        typer.echo("Create it with: mkdir -p ~/.config/automeister/macros")
        return

    macros = load_macros()

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
