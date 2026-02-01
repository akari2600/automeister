"""Configuration management for Automeister."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DisplayConfig:
    """Display-related configuration."""

    display: str = ":0"
    default_screen: int = 0


@dataclass
class CaptureConfig:
    """Screen capture configuration."""

    tool: str = "scrot"  # "scrot" or "maim"
    default_format: str = "png"
    quality: int = 100


@dataclass
class TimeoutConfig:
    """Timeout settings."""

    default_command: float = 30.0
    screen_capture: float = 10.0
    shell_command: float = 60.0


@dataclass
class MouseConfig:
    """Mouse control configuration."""

    default_move_duration: float = 0.0
    default_click_delay: float = 0.05


@dataclass
class KeyboardConfig:
    """Keyboard control configuration."""

    default_type_delay: int = 12  # milliseconds between keystrokes
    default_key_delay: float = 0.05


@dataclass
class Config:
    """Main configuration for Automeister."""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    mouse: MouseConfig = field(default_factory=MouseConfig)
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from a dictionary."""
        config = cls()

        if "display" in data:
            config.display = DisplayConfig(**data["display"])
        if "capture" in data:
            config.capture = CaptureConfig(**data["capture"])
        if "timeouts" in data:
            config.timeouts = TimeoutConfig(**data["timeouts"])
        if "mouse" in data:
            config.mouse = MouseConfig(**data["mouse"])
        if "keyboard" in data:
            config.keyboard = KeyboardConfig(**data["keyboard"])

        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert Config to a dictionary."""
        return {
            "display": {
                "display": self.display.display,
                "default_screen": self.display.default_screen,
            },
            "capture": {
                "tool": self.capture.tool,
                "default_format": self.capture.default_format,
                "quality": self.capture.quality,
            },
            "timeouts": {
                "default_command": self.timeouts.default_command,
                "screen_capture": self.timeouts.screen_capture,
                "shell_command": self.timeouts.shell_command,
            },
            "mouse": {
                "default_move_duration": self.mouse.default_move_duration,
                "default_click_delay": self.mouse.default_click_delay,
            },
            "keyboard": {
                "default_type_delay": self.keyboard.default_type_delay,
                "default_key_delay": self.keyboard.default_key_delay,
            },
        }


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_home) / "automeister" / "config.yaml"


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file.

    Args:
        config_path: Optional path to config file. If None, uses default location.

    Returns:
        Config object with loaded or default values.
    """
    if config_path is None:
        config_path = get_config_path()

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return Config.from_dict(data)

    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Config object to save.
        config_path: Optional path to config file. If None, uses default location.
    """
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)


# Global config instance - loaded lazily
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload the global configuration from disk."""
    global _config
    _config = load_config()
    return _config
