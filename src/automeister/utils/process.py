"""Subprocess utilities for running external commands."""

import subprocess


class CommandError(Exception):
    """Raised when a command fails to execute."""

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed with code {returncode}: {stderr}")


class CommandNotFoundError(Exception):
    """Raised when a required command is not found."""

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"Command '{command}' not found. Please install it.")


def run_command(
    cmd: list[str],
    timeout: float | None = None,
    check: bool = True,
    capture_output: bool = True,
    input_data: str | None = None,
) -> str:
    """
    Run a subprocess command and return stdout.

    Args:
        cmd: Command and arguments as a list
        timeout: Optional timeout in seconds
        check: If True, raise CommandError on non-zero exit
        capture_output: If True, capture stdout and stderr
        input_data: Optional string to pass to stdin

    Returns:
        stdout as a string (empty string if not captured)

    Raises:
        CommandNotFoundError: If the command is not found
        CommandError: If the command fails and check=True
        subprocess.TimeoutExpired: If the command times out
    """
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            input=input_data,
        )

        if check and result.returncode != 0:
            raise CommandError(
                command=" ".join(cmd),
                returncode=result.returncode,
                stderr=result.stderr.strip() if result.stderr else "",
            )

        return result.stdout.strip() if result.stdout else ""

    except FileNotFoundError as e:
        raise CommandNotFoundError(cmd[0]) from e


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in the system PATH.

    Args:
        command: The command name to check

    Returns:
        True if the command exists, False otherwise
    """
    try:
        subprocess.run(
            ["which", command],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
