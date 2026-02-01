"""Variable context and template rendering for macros."""

import os
import subprocess
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError


class MacroContext:
    """
    Execution context for a macro.

    Manages variables, parameters, and template rendering.
    """

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        vars: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize a macro context.

        Args:
            params: Runtime parameters passed to the macro
            vars: Default variables defined in the macro
        """
        self._params = params or {}
        self._vars = vars or {}
        self._runtime_vars: dict[str, Any] = {}

        # Set up Jinja2 environment
        self._env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            variable_start_string="{{",
            variable_end_string="}}",
        )

        # Register custom functions
        self._env.globals["env"] = self._get_env
        self._env.globals["shell"] = self._run_shell

        # Register filters
        self._env.filters["upper"] = str.upper
        self._env.filters["lower"] = str.lower
        self._env.filters["strip"] = str.strip
        self._env.filters["title"] = str.title
        self._env.filters["int"] = int
        self._env.filters["float"] = float
        self._env.filters["bool"] = bool
        self._env.filters["str"] = str
        self._env.filters["default"] = lambda v, d: v if v is not None else d

    def _get_env(self, name: str, default: str = "") -> str:
        """Get an environment variable."""
        return os.environ.get(name, default)

    def _run_shell(self, command: str, timeout: float = 30.0) -> str:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                ["sh", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    @property
    def variables(self) -> dict[str, Any]:
        """Get all current variables."""
        # Order of precedence: runtime vars > params > default vars
        result: dict[str, Any] = {}
        result.update(self._vars)
        result.update(self._params)
        result.update(self._runtime_vars)
        return result

    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self.variables.get(name, default)

    def set(self, name: str, value: Any) -> None:
        """Set a runtime variable."""
        self._runtime_vars[name] = value

    def render(self, template_str: str) -> str:
        """
        Render a template string with current context.

        Args:
            template_str: String potentially containing {{ }} expressions

        Returns:
            Rendered string with expressions evaluated

        Raises:
            ValueError: If template rendering fails
        """
        if "{{" not in template_str:
            # No templating needed
            return template_str

        try:
            template = self._env.from_string(template_str)
            return template.render(**self.variables)
        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error: {e}") from e
        except UndefinedError as e:
            raise ValueError(f"Undefined variable: {e}") from e

    def render_value(self, value: Any) -> Any:
        """
        Render a value, handling strings with templates.

        Args:
            value: Any value, will only render if string

        Returns:
            Rendered value
        """
        if isinstance(value, str):
            return self.render(value)
        if isinstance(value, dict):
            return {k: self.render_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.render_value(v) for v in value]
        return value

    def evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a condition expression.

        Args:
            condition: Condition string (Jinja2 expression)

        Returns:
            True if condition evaluates to truthy, False otherwise
        """
        # Wrap condition in {{ }} if not already templated
        if "{{" not in condition:
            condition = "{{ " + condition + " }}"

        try:
            result = self.render(condition)
            # Handle common truthy/falsy values
            if result.lower() in ("true", "yes", "1"):
                return True
            if result.lower() in ("false", "no", "0", "none", ""):
                return False
            return bool(result)
        except ValueError:
            return False

    def copy(self) -> "MacroContext":
        """Create a copy of this context."""
        ctx = MacroContext(
            params=self._params.copy(),
            vars=self._vars.copy(),
        )
        ctx._runtime_vars = self._runtime_vars.copy()
        return ctx
