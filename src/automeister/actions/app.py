"""Application launching actions."""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from automeister.actions import window
from automeister.config import get_config
from automeister.utils.process import check_command_exists, run_command


def _get_gui_env() -> dict[str, str]:
    """Get environment with DISPLAY set for GUI applications."""
    env = os.environ.copy()
    if "DISPLAY" not in env:
        config = get_config()
        env["DISPLAY"] = config.display.display
    return env


class AppError(Exception):
    """Raised when application operations fail."""

    pass


@dataclass
class AppInfo:
    """Information about an installed application."""

    name: str
    desktop_file: str
    exec_cmd: str | None = None
    icon: str | None = None
    comment: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "desktop_file": self.desktop_file,
            "exec_cmd": self.exec_cmd,
            "icon": self.icon,
            "comment": self.comment,
        }


def _get_desktop_file_dirs() -> list[Path]:
    """Get directories containing .desktop files."""
    dirs = []

    # System directories
    system_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        "/var/lib/flatpak/exports/share/applications",
        "/var/lib/snapd/desktop/applications",
    ]
    for d in system_dirs:
        path = Path(d)
        if path.exists():
            dirs.append(path)

    # User directories
    user_dirs = [
        Path.home() / ".local/share/applications",
        Path.home() / ".local/share/flatpak/exports/share/applications",
    ]
    for d in user_dirs:
        if d.exists():
            dirs.append(d)

    return dirs


def _parse_desktop_file(path: Path) -> AppInfo | None:
    """Parse a .desktop file and extract app info."""
    try:
        name = None
        exec_cmd = None
        icon = None
        comment = None
        is_app = False

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            in_desktop_entry = False
            for line in f:
                line = line.strip()

                if line == "[Desktop Entry]":
                    in_desktop_entry = True
                    continue
                elif line.startswith("[") and line.endswith("]"):
                    in_desktop_entry = False
                    continue

                if not in_desktop_entry:
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "Name" and name is None:  # Take first Name entry
                    name = value
                elif key == "Exec":
                    exec_cmd = value
                elif key == "Icon":
                    icon = value
                elif key == "Comment" and comment is None:
                    comment = value
                elif key == "Type" and value == "Application":
                    is_app = True

        if name and is_app:
            return AppInfo(
                name=name,
                desktop_file=str(path),
                exec_cmd=exec_cmd,
                icon=icon,
                comment=comment,
            )
    except Exception:
        pass

    return None


def list_apps(search: str | None = None) -> list[AppInfo]:
    """
    List installed applications.

    Args:
        search: Optional search string to filter by name (case-insensitive).

    Returns:
        List of AppInfo objects.
    """
    apps = []
    seen_names = set()

    for dir_path in _get_desktop_file_dirs():
        for desktop_file in dir_path.glob("*.desktop"):
            app_info = _parse_desktop_file(desktop_file)
            if app_info and app_info.name not in seen_names:
                if search is None or search.lower() in app_info.name.lower():
                    apps.append(app_info)
                    seen_names.add(app_info.name)

    return sorted(apps, key=lambda a: a.name.lower())


def find_app(name: str) -> AppInfo | None:
    """
    Find an application by name.

    Args:
        name: Application name (case-insensitive, supports partial match).

    Returns:
        AppInfo if found, None otherwise.
    """
    name_lower = name.lower()

    # First try exact match
    for dir_path in _get_desktop_file_dirs():
        for desktop_file in dir_path.glob("*.desktop"):
            app_info = _parse_desktop_file(desktop_file)
            if app_info and app_info.name.lower() == name_lower:
                return app_info

    # Then try substring match
    for dir_path in _get_desktop_file_dirs():
        for desktop_file in dir_path.glob("*.desktop"):
            app_info = _parse_desktop_file(desktop_file)
            if app_info and name_lower in app_info.name.lower():
                return app_info

    # Try matching desktop file name (without .desktop extension)
    for dir_path in _get_desktop_file_dirs():
        for desktop_file in dir_path.glob("*.desktop"):
            if name_lower in desktop_file.stem.lower():
                app_info = _parse_desktop_file(desktop_file)
                if app_info:
                    return app_info

    return None


def open_app(
    name: str,
    wait_for_window: bool = False,
    window_timeout: float = 10.0,
) -> AppInfo:
    """
    Open an application by name.

    Args:
        name: Application name or command.
        wait_for_window: If True, wait for application window to appear.
        window_timeout: Timeout for waiting for window (seconds).

    Returns:
        AppInfo of the launched application.

    Raises:
        AppError: If application not found or failed to launch.
    """
    # First try to find as a .desktop application
    app_info = find_app(name)

    if app_info:
        # Use gtk-launch to launch .desktop file
        desktop_name = Path(app_info.desktop_file).stem

        if check_command_exists("gtk-launch"):
            try:
                subprocess.Popen(
                    ["gtk-launch", desktop_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    env=_get_gui_env(),
                )
            except Exception as e:
                raise AppError(f"Failed to launch {name}: {e}")
        else:
            # Fallback: try to run the Exec command directly
            if app_info.exec_cmd:
                # Remove field codes like %f, %u, etc.
                exec_cmd = app_info.exec_cmd
                for code in ["%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N",
                             "%i", "%c", "%k", "%v", "%m"]:
                    exec_cmd = exec_cmd.replace(code, "")
                exec_cmd = exec_cmd.strip()

                try:
                    subprocess.Popen(
                        exec_cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        env=_get_gui_env(),
                    )
                except Exception as e:
                    raise AppError(f"Failed to launch {name}: {e}")
            else:
                raise AppError(f"No exec command found for {name}")
    else:
        # Try as a direct command
        if check_command_exists(name):
            try:
                subprocess.Popen(
                    [name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    env=_get_gui_env(),
                )
                # Create a basic AppInfo for the command
                app_info = AppInfo(
                    name=name,
                    desktop_file="",
                    exec_cmd=name,
                )
            except Exception as e:
                raise AppError(f"Failed to launch {name}: {e}")
        else:
            raise AppError(
                f"Application not found: {name}. "
                f"Try 'automeister exec app.list' to see available applications."
            )

    if wait_for_window:
        # Wait for a window to appear
        # Try to match by app name or desktop file name
        search_terms = [name]
        if app_info and app_info.name:
            search_terms.append(app_info.name)

        start_time = time.time()
        while time.time() - start_time < window_timeout:
            for term in search_terms:
                try:
                    win = window.find_window(title=term)
                    if win:
                        return app_info
                    win = window.find_window(wm_class=term)
                    if win:
                        return app_info
                except Exception:
                    pass
            time.sleep(0.5)

        # Don't fail if window not found, app may have launched successfully
        # but window title doesn't match search terms

    return app_info


def open_file(path: str) -> None:
    """
    Open a file with its default application.

    Args:
        path: Path to the file to open.

    Raises:
        AppError: If file not found or failed to open.
    """
    path_obj = Path(path).expanduser().resolve()

    if not path_obj.exists():
        raise AppError(f"File not found: {path}")

    if check_command_exists("xdg-open"):
        try:
            subprocess.Popen(
                ["xdg-open", str(path_obj)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=_get_gui_env(),
            )
        except Exception as e:
            raise AppError(f"Failed to open {path}: {e}")
    else:
        raise AppError("xdg-open not found. Cannot open files.")


def open_url(url: str) -> None:
    """
    Open a URL in the default browser.

    Args:
        url: URL to open.

    Raises:
        AppError: If failed to open URL.
    """
    if check_command_exists("xdg-open"):
        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=_get_gui_env(),
            )
        except Exception as e:
            raise AppError(f"Failed to open URL {url}: {e}")
    else:
        raise AppError("xdg-open not found. Cannot open URLs.")
