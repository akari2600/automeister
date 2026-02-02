"""Window management actions using wmctrl and xdotool."""

import re
import time
from dataclasses import dataclass

from automeister.utils.process import check_command_exists, run_command


class WindowError(Exception):
    """Raised when window operations fail."""

    pass


@dataclass
class WindowInfo:
    """Information about a window."""

    window_id: str
    desktop: int
    pid: int
    x: int
    y: int
    width: int
    height: int
    wm_class: str
    hostname: str
    title: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "window_id": self.window_id,
            "desktop": self.desktop,
            "pid": self.pid,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "wm_class": self.wm_class,
            "hostname": self.hostname,
            "title": self.title,
        }


def _get_wmctrl_cmd() -> str:
    """Get the wmctrl command."""
    if check_command_exists("wmctrl"):
        return "wmctrl"
    raise WindowError(
        "wmctrl not found. Install with: sudo apt install wmctrl"
    )


def _get_xdotool_cmd() -> str:
    """Get the xdotool command."""
    if check_command_exists("xdotool"):
        return "xdotool"
    raise WindowError(
        "xdotool not found. Install with: sudo apt install xdotool"
    )


def _parse_window_line(line: str) -> WindowInfo | None:
    """Parse a wmctrl -lGpx line into WindowInfo."""
    # Format: window_id desktop pid x y width height wm_class hostname title
    # Example: 0x04000003  0 1234   0    0 1920 1080  Navigator.firefox hostname Firefox
    match = re.match(
        r"(0x[0-9a-f]+)\s+"  # window_id
        r"(-?\d+)\s+"  # desktop
        r"(\d+)\s+"  # pid
        r"(-?\d+)\s+"  # x
        r"(-?\d+)\s+"  # y
        r"(\d+)\s+"  # width
        r"(\d+)\s+"  # height
        r"(\S+)\s+"  # wm_class
        r"(\S+)\s+"  # hostname
        r"(.*)$",  # title
        line,
    )
    if not match:
        return None

    return WindowInfo(
        window_id=match.group(1),
        desktop=int(match.group(2)),
        pid=int(match.group(3)),
        x=int(match.group(4)),
        y=int(match.group(5)),
        width=int(match.group(6)),
        height=int(match.group(7)),
        wm_class=match.group(8),
        hostname=match.group(9),
        title=match.group(10).strip(),
    )


def list_windows(
    title: str | None = None,
    wm_class: str | None = None,
    desktop: int | None = None,
) -> list[WindowInfo]:
    """
    List all windows, optionally filtered.

    Args:
        title: Filter by window title (substring match, case-insensitive).
        wm_class: Filter by WM_CLASS (substring match, case-insensitive).
        desktop: Filter by desktop number.

    Returns:
        List of WindowInfo objects.
    """
    wmctrl = _get_wmctrl_cmd()

    output = run_command([wmctrl, "-lGpx"], timeout=10)
    windows = []

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        window = _parse_window_line(line)
        if window is None:
            continue

        # Apply filters
        if title and title.lower() not in window.title.lower():
            continue
        if wm_class and wm_class.lower() not in window.wm_class.lower():
            continue
        if desktop is not None and window.desktop != desktop:
            continue

        windows.append(window)

    return windows


def get_active_window() -> WindowInfo | None:
    """
    Get the currently active window.

    Returns:
        WindowInfo for active window, or None if not found.
    """
    xdotool = _get_xdotool_cmd()

    try:
        window_id_dec = run_command([xdotool, "getactivewindow"], timeout=5).strip()
        # Convert decimal to hex
        window_id = hex(int(window_id_dec))
    except Exception:
        return None

    # Find window in list
    windows = list_windows()
    for window in windows:
        if int(window.window_id, 16) == int(window_id, 16):
            return window

    return None


def find_window(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> WindowInfo | None:
    """
    Find a specific window.

    Args:
        title: Window title to search for.
        wm_class: WM_CLASS to search for.
        window_id: Specific window ID (hex format).

    Returns:
        WindowInfo if found, None otherwise.
    """
    if window_id:
        windows = list_windows()
        for window in windows:
            if window.window_id.lower() == window_id.lower():
                return window
        return None

    windows = list_windows(title=title, wm_class=wm_class)
    return windows[0] if windows else None


def focus(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> WindowInfo:
    """
    Focus a window (bring to front and activate).

    Args:
        title: Window title to focus.
        wm_class: WM_CLASS to focus.
        window_id: Specific window ID to focus.

    Returns:
        WindowInfo of focused window.

    Raises:
        WindowError: If window not found.
    """
    wmctrl = _get_wmctrl_cmd()

    if window_id:
        run_command([wmctrl, "-i", "-a", window_id], timeout=5)
    elif title:
        run_command([wmctrl, "-a", title], timeout=5)
    else:
        raise WindowError("Must specify title, wm_class, or window_id")

    # Verify and return window info
    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")
    return window


def move(
    x: int,
    y: int,
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> WindowInfo:
    """
    Move a window to a position.

    Args:
        x: X coordinate.
        y: Y coordinate.
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.

    Returns:
        WindowInfo of moved window.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    # Move window: -e gravity,x,y,width,height (-1 means don't change)
    run_command(
        [wmctrl, "-i", "-r", window.window_id, "-e", f"0,{x},{y},-1,-1"],
        timeout=5,
    )

    # Return updated info
    return find_window(window_id=window.window_id) or window


def resize(
    width: int,
    height: int,
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> WindowInfo:
    """
    Resize a window.

    Args:
        width: New width.
        height: New height.
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.

    Returns:
        WindowInfo of resized window.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    # Resize window: -e gravity,x,y,width,height (-1 means don't change)
    run_command(
        [wmctrl, "-i", "-r", window.window_id, "-e", f"0,-1,-1,{width},{height}"],
        timeout=5,
    )

    # Return updated info
    return find_window(window_id=window.window_id) or window


def minimize(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> None:
    """
    Minimize a window.

    Args:
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.
    """
    xdotool = _get_xdotool_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    # Convert hex to decimal for xdotool
    win_id_dec = str(int(window.window_id, 16))
    run_command([xdotool, "windowminimize", win_id_dec], timeout=5)


def maximize(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> None:
    """
    Maximize a window.

    Args:
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    run_command(
        [wmctrl, "-i", "-r", window.window_id, "-b", "add,maximized_vert,maximized_horz"],
        timeout=5,
    )


def unmaximize(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> None:
    """
    Unmaximize a window.

    Args:
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    run_command(
        [wmctrl, "-i", "-r", window.window_id, "-b", "remove,maximized_vert,maximized_horz"],
        timeout=5,
    )


def close(
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> None:
    """
    Close a window gracefully.

    Args:
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    run_command([wmctrl, "-i", "-c", window.window_id], timeout=5)


def wait_for(
    title: str | None = None,
    wm_class: str | None = None,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> WindowInfo:
    """
    Wait for a window to appear.

    Args:
        title: Window title to wait for.
        wm_class: WM_CLASS to wait for.
        timeout: Maximum time to wait in seconds.
        interval: Time between checks in seconds.

    Returns:
        WindowInfo when window appears.

    Raises:
        WindowError: If timeout is reached.
    """
    if not title and not wm_class:
        raise WindowError("Must specify title or wm_class to wait for")

    start_time = time.time()

    while time.time() - start_time < timeout:
        window = find_window(title=title, wm_class=wm_class)
        if window:
            return window
        time.sleep(interval)

    raise WindowError(
        f"Window not found within {timeout} seconds: {title or wm_class}"
    )


def set_desktop(
    desktop: int,
    title: str | None = None,
    wm_class: str | None = None,
    window_id: str | None = None,
) -> None:
    """
    Move a window to a specific desktop.

    Args:
        desktop: Desktop number (0-indexed).
        title: Window title.
        wm_class: WM_CLASS.
        window_id: Specific window ID.
    """
    wmctrl = _get_wmctrl_cmd()

    window = find_window(title=title, wm_class=wm_class, window_id=window_id)
    if window is None:
        raise WindowError(f"Window not found: {title or wm_class or window_id}")

    run_command(
        [wmctrl, "-i", "-r", window.window_id, "-t", str(desktop)],
        timeout=5,
    )


def get_desktop_count() -> int:
    """
    Get the number of desktops.

    Returns:
        Number of desktops.
    """
    wmctrl = _get_wmctrl_cmd()

    output = run_command([wmctrl, "-d"], timeout=5)
    return len([line for line in output.strip().split("\n") if line.strip()])


def get_current_desktop() -> int:
    """
    Get the current desktop number.

    Returns:
        Current desktop number (0-indexed).
    """
    wmctrl = _get_wmctrl_cmd()

    output = run_command([wmctrl, "-d"], timeout=5)
    for line in output.strip().split("\n"):
        if "*" in line:
            # Format: 0  * DG: ... (asterisk marks current)
            parts = line.split()
            if parts:
                return int(parts[0])
    return 0


def switch_desktop(desktop: int) -> None:
    """
    Switch to a specific desktop.

    Args:
        desktop: Desktop number (0-indexed).
    """
    wmctrl = _get_wmctrl_cmd()

    run_command([wmctrl, "-s", str(desktop)], timeout=5)
