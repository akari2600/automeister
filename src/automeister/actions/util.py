"""Utility actions."""

import time

from automeister.config import get_config
from automeister.utils.process import run_command


def delay(seconds: float) -> None:
    """
    Wait for a specified amount of time.

    Args:
        seconds: Number of seconds to wait
    """
    time.sleep(seconds)


def notify(
    message: str,
    title: str | None = None,
    urgency: str | None = None,
    timeout: int | None = None,
) -> None:
    """
    Show a desktop notification.

    Args:
        message: Notification message body
        title: Optional notification title
        urgency: Urgency level ("low", "normal", "critical")
        timeout: Display duration in milliseconds
    """
    config = get_config()

    cmd = ["notify-send"]

    if urgency:
        cmd.extend(["--urgency", urgency])

    if timeout is not None:
        cmd.extend(["--expire-time", str(timeout)])

    if title:
        cmd.append(title)

    cmd.append(message)

    run_command(cmd, timeout=config.timeouts.default_command)


def clipboard_get() -> str:
    """
    Get the current clipboard content.

    Returns:
        Clipboard content as a string
    """
    config = get_config()
    return run_command(
        ["xclip", "-selection", "clipboard", "-o"],
        timeout=config.timeouts.default_command,
    )


def clipboard_set(text: str) -> None:
    """
    Set the clipboard content.

    Args:
        text: Text to copy to clipboard
    """
    config = get_config()
    run_command(
        ["xclip", "-selection", "clipboard"],
        timeout=config.timeouts.default_command,
        input_data=text,
    )


def shell(
    command: str,
    timeout: float | None = None,
) -> str:
    """
    Run an arbitrary shell command.

    Args:
        command: Shell command to execute
        timeout: Optional timeout in seconds

    Returns:
        Command stdout as a string

    Raises:
        CommandError: If the command fails
    """
    config = get_config()
    actual_timeout = timeout if timeout is not None else config.timeouts.shell_command

    return run_command(
        ["sh", "-c", command],
        timeout=actual_timeout,
    )
