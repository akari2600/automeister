"""Tests for the macro context module."""

import pytest

from automeister.macro.context import MacroContext


class TestMacroContext:
    """Tests for MacroContext."""

    def test_init_empty(self):
        """Test creating empty context."""
        ctx = MacroContext()
        assert ctx.variables == {}

    def test_init_with_params(self):
        """Test creating context with parameters."""
        ctx = MacroContext(params={"user": "john", "count": 5})
        assert ctx.get("user") == "john"
        assert ctx.get("count") == 5

    def test_init_with_vars(self):
        """Test creating context with default vars."""
        ctx = MacroContext(vars={"base_url": "http://example.com"})
        assert ctx.get("base_url") == "http://example.com"

    def test_set_and_get(self):
        """Test setting and getting runtime variables."""
        ctx = MacroContext()
        ctx.set("my_var", "value")
        assert ctx.get("my_var") == "value"

    def test_get_with_default(self):
        """Test getting nonexistent variable with default."""
        ctx = MacroContext()
        assert ctx.get("missing", "default") == "default"

    def test_variable_precedence(self):
        """Test that runtime vars override params which override defaults."""
        ctx = MacroContext(
            params={"var": "from_param"},
            vars={"var": "from_default"},
        )
        # Params override default vars
        assert ctx.get("var") == "from_param"

        # Runtime vars override params
        ctx.set("var", "from_runtime")
        assert ctx.get("var") == "from_runtime"


class TestMacroContextRender:
    """Tests for template rendering."""

    def test_render_simple_variable(self):
        """Test rendering a simple variable."""
        ctx = MacroContext(params={"name": "World"})
        result = ctx.render("Hello, {{ name }}!")
        assert result == "Hello, World!"

    def test_render_no_template(self):
        """Test rendering string without template."""
        ctx = MacroContext()
        result = ctx.render("No templates here")
        assert result == "No templates here"

    def test_render_with_filters(self):
        """Test rendering with Jinja2 filters."""
        ctx = MacroContext(params={"name": "john"})
        assert ctx.render("{{ name | upper }}") == "JOHN"
        assert ctx.render("{{ name | title }}") == "John"

    def test_render_undefined_variable(self):
        """Test rendering with undefined variable raises error."""
        ctx = MacroContext()
        with pytest.raises(ValueError, match="Undefined variable"):
            ctx.render("{{ undefined_var }}")

    def test_render_syntax_error(self):
        """Test rendering with syntax error raises error."""
        ctx = MacroContext()
        with pytest.raises(ValueError, match="Template syntax error"):
            ctx.render("{{ invalid syntax }}")

    def test_render_value_string(self):
        """Test render_value with string."""
        ctx = MacroContext(params={"x": "10"})
        result = ctx.render_value("Value is {{ x }}")
        assert result == "Value is 10"

    def test_render_value_dict(self):
        """Test render_value with dict."""
        ctx = MacroContext(params={"user": "john"})
        result = ctx.render_value({"name": "{{ user }}", "count": 5})
        assert result == {"name": "john", "count": 5}

    def test_render_value_list(self):
        """Test render_value with list."""
        ctx = MacroContext(params={"a": "1", "b": "2"})
        result = ctx.render_value(["{{ a }}", "{{ b }}"])
        assert result == ["1", "2"]

    def test_render_value_non_string(self):
        """Test render_value passes through non-strings."""
        ctx = MacroContext()
        assert ctx.render_value(42) == 42
        assert ctx.render_value(3.14) == 3.14
        assert ctx.render_value(True) is True


class TestMacroContextConditions:
    """Tests for condition evaluation."""

    def test_evaluate_true_condition(self):
        """Test evaluating a true condition."""
        ctx = MacroContext(params={"enabled": True})
        assert ctx.evaluate_condition("enabled") is True

    def test_evaluate_false_condition(self):
        """Test evaluating a false condition."""
        ctx = MacroContext(params={"enabled": False})
        assert ctx.evaluate_condition("enabled") is False

    def test_evaluate_comparison(self):
        """Test evaluating a comparison."""
        ctx = MacroContext(params={"count": 10})
        assert ctx.evaluate_condition("count > 5") is True
        assert ctx.evaluate_condition("count < 5") is False
        assert ctx.evaluate_condition("count == 10") is True

    def test_evaluate_string_truthy(self):
        """Test string truthy values."""
        ctx = MacroContext()
        ctx.set("result", "true")
        assert ctx.evaluate_condition("result") is True

        ctx.set("result", "false")
        assert ctx.evaluate_condition("result") is False

        ctx.set("result", "")
        assert ctx.evaluate_condition("result") is False

    def test_evaluate_invalid_returns_false(self):
        """Test that invalid conditions return False."""
        ctx = MacroContext()
        assert ctx.evaluate_condition("{{ undefined }}") is False


class TestMacroContextCopy:
    """Tests for context copying."""

    def test_copy(self):
        """Test copying a context."""
        original = MacroContext(
            params={"user": "john"},
            vars={"base": "value"},
        )
        original.set("runtime", "data")

        copy = original.copy()

        # Copy has same values
        assert copy.get("user") == "john"
        assert copy.get("base") == "value"
        assert copy.get("runtime") == "data"

        # Modifying copy doesn't affect original
        copy.set("new_var", "new_value")
        assert copy.get("new_var") == "new_value"
        assert original.get("new_var") is None
