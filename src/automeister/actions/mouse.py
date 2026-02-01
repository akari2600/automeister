"""Mouse control actions."""

import time
from typing import Literal

from automeister.config import get_config
from automeister.utils.process import run_command

Button = Literal["left", "middle", "right"]
BUTTON_MAP = {"left": "1", "middle": "2", "right": "3"}


def move(
    x: int,
    y: int,
    relative: bool = False,
    duration: float | None = None,
) -> None:
    """
    Move the mouse cursor to a position.

    Args:
        x: X coordinate (or delta if relative)
        y: Y coordinate (or delta if relative)
        relative: If True, move relative to current position
        duration: Animation duration in seconds (0 for instant)
    """
    config = get_config()
    actual_duration = duration if duration is not None else config.mouse.default_move_duration

    cmd = ["xdotool"]

    if relative:
        cmd.append("mousemove_relative")
        if actual_duration > 0:
            # For smooth movement, we simulate it with steps
            _smooth_relative_move(x, y, actual_duration)
            return
    else:
        cmd.append("mousemove")

    cmd.extend([str(x), str(y)])
    run_command(cmd, timeout=config.timeouts.default_command)


def _smooth_relative_move(dx: int, dy: int, duration: float) -> None:
    """Perform smooth relative mouse movement."""
    steps = max(10, int(duration * 60))  # ~60 fps
    step_delay = duration / steps
    step_x = dx / steps
    step_y = dy / steps

    for _ in range(steps):
        run_command(
            ["xdotool", "mousemove_relative", "--", str(int(step_x)), str(int(step_y))],
            check=False,
        )
        time.sleep(step_delay)


def click(
    button: Button = "left",
    count: int = 1,
) -> None:
    """
    Click the mouse button at current position.

    Args:
        button: Which button to click ("left", "middle", "right")
        count: Number of clicks (1 for single, 2 for double, etc.)
    """
    config = get_config()
    button_num = BUTTON_MAP.get(button, "1")

    cmd = ["xdotool", "click"]

    if count > 1:
        cmd.extend(["--repeat", str(count)])
        cmd.extend(["--delay", str(int(config.mouse.default_click_delay * 1000))])

    cmd.append(button_num)
    run_command(cmd, timeout=config.timeouts.default_command)


def click_at(
    x: int,
    y: int,
    button: Button = "left",
    count: int = 1,
) -> None:
    """
    Move to a position and click.

    Args:
        x: X coordinate
        y: Y coordinate
        button: Which button to click
        count: Number of clicks
    """
    move(x, y)
    click(button, count)


def drag(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    button: Button = "left",
    duration: float | None = None,
) -> None:
    """
    Drag from one position to another.

    Args:
        x1: Start X coordinate
        y1: Start Y coordinate
        x2: End X coordinate
        y2: End Y coordinate
        button: Which button to hold during drag
        duration: Duration of the drag operation in seconds
    """
    config = get_config()
    button_num = BUTTON_MAP.get(button, "1")
    actual_duration = duration if duration is not None else 0.5

    # Move to start position
    move(x1, y1)

    # Press and hold
    run_command(
        ["xdotool", "mousedown", button_num],
        timeout=config.timeouts.default_command,
    )

    # Move to end position with animation
    if actual_duration > 0:
        steps = max(10, int(actual_duration * 60))
        step_delay = actual_duration / steps
        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps

        current_x, current_y = float(x1), float(y1)
        for _ in range(steps):
            current_x += dx
            current_y += dy
            run_command(
                ["xdotool", "mousemove", str(int(current_x)), str(int(current_y))],
                check=False,
            )
            time.sleep(step_delay)
    else:
        move(x2, y2)

    # Release
    run_command(
        ["xdotool", "mouseup", button_num],
        timeout=config.timeouts.default_command,
    )


def scroll(
    amount: int,
    horizontal: bool = False,
) -> None:
    """
    Scroll the mouse wheel.

    Args:
        amount: Number of scroll units (positive = down/right, negative = up/left)
        horizontal: If True, scroll horizontally
    """
    config = get_config()

    if amount == 0:
        return

    if horizontal:
        # xdotool uses button 6 for left, 7 for right
        button = "7" if amount > 0 else "6"
    else:
        # xdotool uses button 4 for up, 5 for down
        button = "5" if amount > 0 else "4"

    cmd = ["xdotool", "click", "--repeat", str(abs(amount)), button]
    run_command(cmd, timeout=config.timeouts.default_command)


def get_position() -> tuple[int, int]:
    """
    Get the current mouse cursor position.

    Returns:
        Tuple of (x, y) coordinates
    """
    config = get_config()
    output = run_command(
        ["xdotool", "getmouselocation", "--shell"],
        timeout=config.timeouts.default_command,
    )

    # Parse output like "X=123\nY=456\n..."
    x, y = 0, 0
    for line in output.split("\n"):
        if line.startswith("X="):
            x = int(line[2:])
        elif line.startswith("Y="):
            y = int(line[2:])

    return (x, y)
