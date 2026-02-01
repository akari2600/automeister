"""YAML macro parser for Automeister."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


class MacroParseError(Exception):
    """Raised when a macro fails to parse."""

    def __init__(self, message: str, file_path: str | None = None, line: int | None = None) -> None:
        self.file_path = file_path
        self.line = line
        location = ""
        if file_path:
            location = f" in {file_path}"
        if line:
            location += f" at line {line}"
        super().__init__(f"{message}{location}")


@dataclass
class MacroParameter:
    """A parameter definition for a macro."""

    name: str
    type: Literal["string", "integer", "boolean", "float", "list"] = "string"
    required: bool = True
    default: Any = None
    description: str = ""

    def validate(self, value: Any) -> Any:
        """Validate and coerce a parameter value."""
        if value is None:
            if self.required and self.default is None:
                raise ValueError(f"Required parameter '{self.name}' not provided")
            return self.default

        if self.type == "string":
            return str(value)
        elif self.type == "integer":
            try:
                return int(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Parameter '{self.name}' must be an integer") from e
        elif self.type == "float":
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Parameter '{self.name}' must be a float") from e
        elif self.type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ("true", "yes", "1", "on"):
                    return True
                if value.lower() in ("false", "no", "0", "off"):
                    return False
            raise ValueError(f"Parameter '{self.name}' must be a boolean")
        elif self.type == "list":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(",")]
            raise ValueError(f"Parameter '{self.name}' must be a list")
        else:
            return value


@dataclass
class MacroAction:
    """A single action in a macro."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int) -> "MacroAction":
        """Create a MacroAction from a dictionary."""
        if "action" not in data:
            raise MacroParseError(f"Action at index {index} missing 'action' field")

        action = data.pop("action")
        condition = data.pop("if", None)
        name = data.pop("name", None)

        return cls(
            action=action,
            args=data,
            condition=condition,
            name=name,
        )


@dataclass
class Macro:
    """A macro definition."""

    name: str
    description: str = ""
    parameters: list[MacroParameter] = field(default_factory=list)
    vars: dict[str, Any] = field(default_factory=dict)
    actions: list[MacroAction] = field(default_factory=list)
    file_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], file_path: str | None = None) -> "Macro":
        """Create a Macro from a dictionary."""
        if "name" not in data:
            raise MacroParseError("Macro missing 'name' field", file_path)

        # Parse parameters
        parameters: list[MacroParameter] = []
        for param_data in data.get("parameters", []):
            if isinstance(param_data, str):
                # Simple parameter name
                parameters.append(MacroParameter(name=param_data))
            elif isinstance(param_data, dict):
                if "name" not in param_data:
                    raise MacroParseError("Parameter missing 'name' field", file_path)
                parameters.append(
                    MacroParameter(
                        name=param_data["name"],
                        type=param_data.get("type", "string"),
                        required=param_data.get("required", True),
                        default=param_data.get("default"),
                        description=param_data.get("description", ""),
                    )
                )

        # Parse actions
        actions: list[MacroAction] = []
        for i, action_data in enumerate(data.get("actions", [])):
            if not isinstance(action_data, dict):
                raise MacroParseError(f"Action at index {i} must be a dictionary", file_path)
            actions.append(MacroAction.from_dict(action_data.copy(), i))

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=parameters,
            vars=data.get("vars", {}),
            actions=actions,
            file_path=file_path,
        )

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate and process input parameters."""
        validated: dict[str, Any] = {}

        for param in self.parameters:
            value = params.get(param.name)
            validated[param.name] = param.validate(value)

        return validated


def get_macros_dir() -> Path:
    """Get the path to the macros directory."""
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_home) / "automeister" / "macros"


def load_macro(file_path: str | Path) -> Macro:
    """
    Load a macro from a YAML file.

    Args:
        file_path: Path to the macro YAML file

    Returns:
        Parsed Macro object

    Raises:
        MacroParseError: If the macro fails to parse
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Macro file not found: {path}")

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise MacroParseError(f"Invalid YAML: {e}", str(path)) from e

    if not isinstance(data, dict):
        raise MacroParseError("Macro must be a YAML dictionary", str(path))

    return Macro.from_dict(data, str(path))


def load_macros(directory: str | Path | None = None) -> dict[str, Macro]:
    """
    Load all macros from a directory.

    Args:
        directory: Path to directory containing macro files.
                   If None, uses the default macros directory.

    Returns:
        Dictionary mapping macro names to Macro objects
    """
    if directory is None:
        directory = get_macros_dir()
    else:
        directory = Path(directory)

    if not directory.exists():
        return {}

    macros: dict[str, Macro] = {}

    for yaml_file in directory.glob("*.yaml"):
        try:
            macro = load_macro(yaml_file)
            macros[macro.name] = macro
        except (MacroParseError, FileNotFoundError):
            # Skip invalid macros
            continue

    for yml_file in directory.glob("*.yml"):
        try:
            macro = load_macro(yml_file)
            macros[macro.name] = macro
        except (MacroParseError, FileNotFoundError):
            continue

    return macros


def find_macro(name: str, directory: str | Path | None = None) -> Macro | None:
    """
    Find a macro by name.

    Args:
        name: Name of the macro to find
        directory: Optional directory to search in

    Returns:
        Macro if found, None otherwise
    """
    if directory is None:
        directory = get_macros_dir()
    else:
        directory = Path(directory)

    # First try exact file match
    for ext in (".yaml", ".yml"):
        path = directory / f"{name}{ext}"
        if path.exists():
            macro = load_macro(path)
            if macro.name == name:
                return macro

    # Then search all macros
    macros = load_macros(directory)
    return macros.get(name)
