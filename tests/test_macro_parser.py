"""Tests for the macro parser module."""

import tempfile
from pathlib import Path

import pytest

from automeister.macro.parser import (
    Macro,
    MacroAction,
    MacroParameter,
    MacroParseError,
    load_macro,
)


class TestMacroParameter:
    """Tests for MacroParameter."""

    def test_validate_string(self):
        """Test string parameter validation."""
        param = MacroParameter(name="test", type="string")
        assert param.validate("hello") == "hello"
        assert param.validate(123) == "123"

    def test_validate_integer(self):
        """Test integer parameter validation."""
        param = MacroParameter(name="test", type="integer")
        assert param.validate("42") == 42
        assert param.validate(42) == 42

    def test_validate_integer_invalid(self):
        """Test integer validation with invalid input."""
        param = MacroParameter(name="test", type="integer")
        with pytest.raises(ValueError, match="must be an integer"):
            param.validate("not a number")

    def test_validate_float(self):
        """Test float parameter validation."""
        param = MacroParameter(name="test", type="float")
        assert param.validate("3.14") == 3.14
        assert param.validate(3.14) == 3.14

    def test_validate_boolean(self):
        """Test boolean parameter validation."""
        param = MacroParameter(name="test", type="boolean")
        assert param.validate("true") is True
        assert param.validate("false") is False
        assert param.validate("yes") is True
        assert param.validate("no") is False
        assert param.validate(True) is True
        assert param.validate(False) is False

    def test_validate_list(self):
        """Test list parameter validation."""
        param = MacroParameter(name="test", type="list")
        assert param.validate("a,b,c") == ["a", "b", "c"]
        assert param.validate(["a", "b"]) == ["a", "b"]

    def test_validate_required_missing(self):
        """Test required parameter without value."""
        param = MacroParameter(name="test", type="string", required=True)
        with pytest.raises(ValueError, match="Required parameter"):
            param.validate(None)

    def test_validate_optional_with_default(self):
        """Test optional parameter with default value."""
        param = MacroParameter(
            name="test", type="string", required=False, default="default"
        )
        assert param.validate(None) == "default"


class TestMacroAction:
    """Tests for MacroAction."""

    def test_from_dict_basic(self):
        """Test basic action parsing."""
        data = {"action": "delay", "seconds": 1}
        action = MacroAction.from_dict(data.copy(), 0)
        assert action.action == "delay"
        assert action.args == {"seconds": 1}

    def test_from_dict_with_condition(self):
        """Test action with condition."""
        data = {"action": "click", "if": "some_var == true"}
        action = MacroAction.from_dict(data.copy(), 0)
        assert action.action == "click"
        assert action.condition == "some_var == true"

    def test_from_dict_with_name(self):
        """Test action with name."""
        data = {"action": "delay", "name": "wait step", "seconds": 2}
        action = MacroAction.from_dict(data.copy(), 0)
        assert action.name == "wait step"

    def test_from_dict_missing_action(self):
        """Test parsing fails without action field."""
        data = {"seconds": 1}
        with pytest.raises(MacroParseError, match="missing 'action' field"):
            MacroAction.from_dict(data, 0)


class TestMacro:
    """Tests for Macro."""

    def test_from_dict_minimal(self):
        """Test minimal macro parsing."""
        data = {"name": "test", "actions": []}
        macro = Macro.from_dict(data)
        assert macro.name == "test"
        assert macro.actions == []
        assert macro.parameters == []

    def test_from_dict_with_parameters(self):
        """Test macro with parameters."""
        data = {
            "name": "test",
            "parameters": [
                {"name": "user", "type": "string", "required": True},
                {"name": "count", "type": "integer", "default": 5},
            ],
            "actions": [],
        }
        macro = Macro.from_dict(data)
        assert len(macro.parameters) == 2
        assert macro.parameters[0].name == "user"
        assert macro.parameters[1].default == 5

    def test_from_dict_with_actions(self):
        """Test macro with actions."""
        data = {
            "name": "test",
            "actions": [
                {"action": "delay", "seconds": 1},
                {"action": "notify", "message": "Done"},
            ],
        }
        macro = Macro.from_dict(data)
        assert len(macro.actions) == 2
        assert macro.actions[0].action == "delay"
        assert macro.actions[1].action == "notify"

    def test_from_dict_missing_name(self):
        """Test parsing fails without name."""
        data = {"actions": []}
        with pytest.raises(MacroParseError, match="missing 'name' field"):
            Macro.from_dict(data)

    def test_validate_params(self):
        """Test parameter validation."""
        data = {
            "name": "test",
            "parameters": [
                {"name": "user", "type": "string", "required": True},
                {"name": "count", "type": "integer", "default": 5},
            ],
            "actions": [],
        }
        macro = Macro.from_dict(data)

        result = macro.validate_params({"user": "john"})
        assert result["user"] == "john"
        assert result["count"] == 5


class TestLoadMacro:
    """Tests for load_macro function."""

    def test_load_valid_macro(self):
        """Test loading a valid macro file."""
        content = """
name: test-macro
description: A test macro
actions:
  - action: delay
    seconds: 1
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(content)
            f.flush()

            macro = load_macro(f.name)
            assert macro.name == "test-macro"
            assert macro.description == "A test macro"
            assert len(macro.actions) == 1

            Path(f.name).unlink()

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_macro("/nonexistent/path/macro.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(MacroParseError, match="Invalid YAML"):
                load_macro(f.name)

            Path(f.name).unlink()
