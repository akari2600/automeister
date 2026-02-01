"""Keyboard control actions."""


from automeister.config import get_config
from automeister.utils.process import run_command


def type_text(
    text: str,
    delay: int | None = None,
) -> None:
    """
    Type text using the keyboard.

    Args:
        text: Text to type
        delay: Delay between keystrokes in milliseconds
    """
    config = get_config()
    actual_delay = delay if delay is not None else config.keyboard.default_type_delay

    cmd = ["xdotool", "type", "--delay", str(actual_delay), "--", text]
    run_command(cmd, timeout=config.timeouts.default_command)


def key(
    key_name: str,
    modifiers: list[str] | None = None,
) -> None:
    """
    Press a single key, optionally with modifiers.

    Args:
        key_name: Name of the key (e.g., "Return", "Tab", "a", "F1")
        modifiers: Optional list of modifiers (e.g., ["ctrl", "shift"])

    Examples:
        key("Return")  # Press Enter
        key("c", ["ctrl"])  # Ctrl+C
        key("s", ["ctrl", "shift"])  # Ctrl+Shift+S
    """
    config = get_config()

    if modifiers:
        # Format: ctrl+shift+key
        key_combo = "+".join(modifiers) + "+" + key_name
    else:
        key_combo = key_name

    cmd = ["xdotool", "key", key_combo]
    run_command(cmd, timeout=config.timeouts.default_command)


def hotkey(combo: str) -> None:
    """
    Press a key combination.

    Args:
        combo: Key combination string (e.g., "ctrl+c", "ctrl+shift+s", "alt+F4")

    The combo string is passed directly to xdotool, which expects
    modifiers and key separated by '+'.
    """
    config = get_config()
    cmd = ["xdotool", "key", combo]
    run_command(cmd, timeout=config.timeouts.default_command)


def key_down(key_name: str) -> None:
    """
    Press and hold a key.

    Args:
        key_name: Name of the key to hold
    """
    config = get_config()
    cmd = ["xdotool", "keydown", key_name]
    run_command(cmd, timeout=config.timeouts.default_command)


def key_up(key_name: str) -> None:
    """
    Release a held key.

    Args:
        key_name: Name of the key to release
    """
    config = get_config()
    cmd = ["xdotool", "keyup", key_name]
    run_command(cmd, timeout=config.timeouts.default_command)


# Common key name mappings for convenience
KEY_ALIASES = {
    "enter": "Return",
    "esc": "Escape",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "space": "space",
    "tab": "Tab",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Page_Up",
    "pagedown": "Page_Down",
    "pgup": "Page_Up",
    "pgdn": "Page_Down",
    "insert": "Insert",
    "ins": "Insert",
    "capslock": "Caps_Lock",
    "numlock": "Num_Lock",
    "scrolllock": "Scroll_Lock",
    "printscreen": "Print",
    "prtsc": "Print",
}


def normalize_key(key_name: str) -> str:
    """
    Normalize a key name to xdotool format.

    Args:
        key_name: Key name (case insensitive)

    Returns:
        Normalized key name for xdotool
    """
    lower_key = key_name.lower()
    return KEY_ALIASES.get(lower_key, key_name)
