"""Macro executor for Automeister."""

from typing import TYPE_CHECKING, Any

from automeister.actions import image, keyboard, mouse, screen, util
from automeister.macro.context import MacroContext
from automeister.macro.parser import Macro, MacroAction

if TYPE_CHECKING:
    from automeister.macro.executor import MacroExecutor


class MacroExecutionError(Exception):
    """Raised when a macro fails to execute."""

    def __init__(
        self,
        message: str,
        action_index: int | None = None,
        action_name: str | None = None,
    ) -> None:
        self.action_index = action_index
        self.action_name = action_name
        location = ""
        if action_index is not None:
            location = f" at action {action_index}"
        if action_name:
            location += f" ({action_name})"
        super().__init__(f"{message}{location}")


class LoopBreak(Exception):  # noqa: N818
    """Raised to break out of a loop (control flow, not an error)."""

    pass


class LoopContinue(Exception):  # noqa: N818
    """Raised to continue to next loop iteration (control flow, not an error)."""

    pass


# Registry of action handlers
ACTION_HANDLERS: dict[str, Any] = {}


def register_action(name: str):
    """Decorator to register an action handler."""

    def decorator(func):
        ACTION_HANDLERS[name] = func
        return func

    return decorator


class MacroExecutor:
    """Executes macros with a given context."""

    # Track call depth for recursion protection
    MAX_CALL_DEPTH = 50

    def __init__(self, verbose: bool = False, _call_depth: int = 0) -> None:
        """
        Initialize the executor.

        Args:
            verbose: If True, print action details during execution
            _call_depth: Internal call depth counter for recursion protection
        """
        self.verbose = verbose
        self._call_depth = _call_depth
        self._register_default_actions()

    def _register_default_actions(self) -> None:
        """Register built-in action handlers."""
        # These map action names to handler functions
        pass  # Handlers are registered via decorators

    def execute(self, macro: Macro, params: dict[str, Any] | None = None) -> None:
        """
        Execute a macro.

        Args:
            macro: The macro to execute
            params: Runtime parameters

        Raises:
            MacroExecutionError: If execution fails
        """
        if self._call_depth >= self.MAX_CALL_DEPTH:
            raise MacroExecutionError("Maximum call depth exceeded (possible infinite recursion)")

        # Validate and process parameters
        validated_params = macro.validate_params(params or {})

        # Create execution context
        context = MacroContext(params=validated_params, vars=macro.vars)

        # Execute actions
        self.execute_actions(macro.actions, context)

    def execute_actions(
        self,
        actions: list[MacroAction],
        context: MacroContext,
        start_index: int = 0,
    ) -> Any:
        """
        Execute a list of actions.

        Args:
            actions: List of actions to execute
            context: Execution context
            start_index: Starting index for error reporting

        Returns:
            Result of the last action
        """
        result = None
        for i, action in enumerate(actions):
            result = self._execute_action(action, context, start_index + i)
        return result

    def _execute_action(
        self,
        action: MacroAction,
        context: MacroContext,
        index: int,
    ) -> Any:
        """Execute a single action."""
        # Check condition
        if action.condition:
            if not context.evaluate_condition(action.condition):
                if self.verbose:
                    print(f"Skipping action {index}: condition not met")
                return None

        # Render arguments (but not nested actions)
        rendered_args = self._render_args(action.args, context)

        if self.verbose:
            print(f"Executing: {action.action} {self._summarize_args(rendered_args)}")

        # Find and execute handler
        handler = ACTION_HANDLERS.get(action.action)
        if handler is None:
            raise MacroExecutionError(
                f"Unknown action: {action.action}",
                action_index=index,
                action_name=action.name,
            )

        try:
            result = handler(rendered_args, context, self)
            return result
        except (LoopBreak, LoopContinue):
            # Re-raise loop control exceptions
            raise
        except MacroExecutionError:
            # Re-raise with original context
            raise
        except Exception as e:
            raise MacroExecutionError(
                str(e),
                action_index=index,
                action_name=action.name,
            ) from e

    def _render_args(self, args: dict[str, Any], context: MacroContext) -> dict[str, Any]:
        """Render arguments, preserving action lists for flow control."""
        rendered: dict[str, Any] = {}
        for key, value in args.items():
            # Don't render nested action lists
            if key in ("then", "else", "actions", "catch", "finally"):
                rendered[key] = value
            else:
                rendered[key] = context.render_value(value)
        return rendered

    def _summarize_args(self, args: dict[str, Any]) -> str:
        """Create a summary of args for verbose output."""
        summary = {}
        for key, value in args.items():
            if key in ("then", "else", "actions", "catch", "finally"):
                if isinstance(value, list):
                    summary[key] = f"[{len(value)} actions]"
                else:
                    summary[key] = "..."
            else:
                summary[key] = value
        return str(summary)

    def _parse_actions(self, action_data: list[dict[str, Any]]) -> list[MacroAction]:
        """Parse a list of action dictionaries into MacroAction objects."""
        actions = []
        for i, data in enumerate(action_data):
            if isinstance(data, dict):
                actions.append(MacroAction.from_dict(data.copy(), i))
        return actions

    def create_child_executor(self) -> "MacroExecutor":
        """Create a child executor for subroutine calls."""
        return MacroExecutor(verbose=self.verbose, _call_depth=self._call_depth + 1)


# =============================================================================
# Built-in Action Handlers
# =============================================================================


@register_action("set-var")
def action_set_var(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Set a runtime variable."""
    name = args.get("name")
    value = args.get("value")
    if name is None:
        raise ValueError("set-var requires 'name' argument")
    context.set(name, value)


@register_action("delay")
def action_delay(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Pause execution."""
    seconds = args.get("seconds", args.get("duration", 1.0))
    util.delay(float(seconds))


@register_action("notify")
def action_notify(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Show a notification."""
    message = args.get("message", "")
    title = args.get("title")
    urgency = args.get("urgency")
    timeout = args.get("timeout")
    util.notify(message, title=title, urgency=urgency, timeout=timeout)


@register_action("shell")
def action_shell(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> str:
    """Run a shell command."""
    command = args.get("command", "")
    timeout = args.get("timeout")
    result = util.shell(command, timeout=timeout)

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


@register_action("clipboard.get")
def action_clipboard_get(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> str:
    """Get clipboard content."""
    result = util.clipboard_get()

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


@register_action("clipboard.set")
def action_clipboard_set(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Set clipboard content."""
    text = args.get("text", "")
    util.clipboard_set(text)


# Mouse actions


@register_action("mouse.move")
def action_mouse_move(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Move the mouse."""
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    relative = args.get("relative", False)
    duration = args.get("duration")
    mouse.move(x, y, relative=relative, duration=duration)


@register_action("mouse.click")
def action_mouse_click(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Click the mouse."""
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    mouse.click(button=button, count=count)


@register_action("mouse.click-at")
def action_mouse_click_at(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Move and click."""
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    mouse.click_at(x, y, button=button, count=count)


@register_action("mouse.drag")
def action_mouse_drag(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Drag the mouse."""
    x1 = int(args.get("x1", args.get("from_x", 0)))
    y1 = int(args.get("y1", args.get("from_y", 0)))
    x2 = int(args.get("x2", args.get("to_x", 0)))
    y2 = int(args.get("y2", args.get("to_y", 0)))
    button = args.get("button", "left")
    duration = args.get("duration")
    mouse.drag(x1, y1, x2, y2, button=button, duration=duration)


@register_action("mouse.scroll")
def action_mouse_scroll(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Scroll the mouse wheel."""
    amount = int(args.get("amount", 3))
    horizontal = args.get("horizontal", False)
    mouse.scroll(amount, horizontal=horizontal)


@register_action("mouse.click-image")
def action_mouse_click_image(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Find and click an image."""
    template = args.get("template", args.get("image", ""))
    button = args.get("button", "left")
    offset_x = int(args.get("offset_x", 0))
    offset_y = int(args.get("offset_y", 0))
    timeout = float(args.get("timeout", 0.0))
    threshold = float(args.get("threshold", 0.8))
    region = args.get("region")

    region_tuple = None
    if region:
        if isinstance(region, str):
            region_tuple = screen.parse_region(region)
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            region_tuple = tuple(region)  # type: ignore

    result = image.click_image(
        template,
        button=button,
        offset_x=offset_x,
        offset_y=offset_y,
        timeout=timeout,
        threshold=threshold,
        region=region_tuple,
    )

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result.to_dict())


# Keyboard actions


@register_action("keyboard.type")
def action_keyboard_type(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Type text."""
    text = args.get("text", "")
    delay = args.get("delay")
    keyboard.type_text(text, delay=delay)


@register_action("keyboard.key")
def action_keyboard_key(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Press a key."""
    key_name = args.get("key", "")
    modifiers = args.get("modifiers")
    if isinstance(modifiers, str):
        modifiers = [m.strip() for m in modifiers.split(",")]
    keyboard.key(key_name, modifiers=modifiers)


@register_action("keyboard.hotkey")
def action_keyboard_hotkey(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Press a key combination."""
    combo = args.get("combo", args.get("keys", ""))
    keyboard.hotkey(combo)


# Screen actions


@register_action("screen.capture")
def action_screen_capture(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> str:
    """Capture the screen."""
    output = args.get("output")
    region = args.get("region")
    tool = args.get("tool")

    region_tuple = None
    if region:
        if isinstance(region, str):
            region_tuple = screen.parse_region(region)
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            region_tuple = tuple(region)  # type: ignore

    result = screen.capture(region=region_tuple, output=output, tool=tool)

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


@register_action("screen.find")
def action_screen_find(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> dict | None:
    """Find an image on screen."""
    template = args.get("template", args.get("image", ""))
    threshold = float(args.get("threshold", 0.8))
    region = args.get("region")
    grayscale = args.get("grayscale", False)

    region_tuple = None
    if region:
        if isinstance(region, str):
            region_tuple = screen.parse_region(region)
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            region_tuple = tuple(region)  # type: ignore

    result = image.find_best(
        template,
        threshold=threshold,
        region=region_tuple,
        grayscale=grayscale,
    )

    result_dict = result.to_dict() if result else None

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result_dict)

    return result_dict


@register_action("screen.wait-for")
def action_screen_wait_for(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> dict:
    """Wait for an image to appear."""
    template = args.get("template", args.get("image", ""))
    timeout = float(args.get("timeout", 30.0))
    interval = float(args.get("interval", 0.5))
    threshold = float(args.get("threshold", 0.8))
    region = args.get("region")
    grayscale = args.get("grayscale", False)

    region_tuple = None
    if region:
        if isinstance(region, str):
            region_tuple = screen.parse_region(region)
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            region_tuple = tuple(region)  # type: ignore

    result = image.wait_for(
        template,
        timeout=timeout,
        interval=interval,
        threshold=threshold,
        region=region_tuple,
        grayscale=grayscale,
    )

    result_dict = result.to_dict()

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result_dict)

    return result_dict


@register_action("screen.exists")
def action_screen_exists(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> bool:
    """Check if an image exists on screen."""
    template = args.get("template", args.get("image", ""))
    threshold = float(args.get("threshold", 0.8))
    region = args.get("region")
    grayscale = args.get("grayscale", False)

    region_tuple = None
    if region:
        if isinstance(region, str):
            region_tuple = screen.parse_region(region)
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            region_tuple = tuple(region)  # type: ignore

    result = image.exists(
        template,
        threshold=threshold,
        region=region_tuple,
        grayscale=grayscale,
    )

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


# =============================================================================
# Flow Control Action Handlers
# =============================================================================


@register_action("if")
def action_if(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> Any:
    """Conditional execution with then/else branches."""
    condition = args.get("condition", "")

    # Evaluate condition
    is_true = context.evaluate_condition(condition)

    if is_true:
        then_actions = args.get("then", [])
        if then_actions:
            parsed = executor._parse_actions(then_actions)
            return executor.execute_actions(parsed, context)
    else:
        else_actions = args.get("else", [])
        if else_actions:
            parsed = executor._parse_actions(else_actions)
            return executor.execute_actions(parsed, context)

    return None


@register_action("repeat")
def action_repeat(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Repeat actions a fixed number of times."""
    count = int(args.get("count", 1))
    loop_var = args.get("as", "i")
    actions_data = args.get("actions", [])

    if not actions_data:
        return

    parsed = executor._parse_actions(actions_data)

    for i in range(count):
        context.set(loop_var, i)
        try:
            executor.execute_actions(parsed, context)
        except LoopBreak:
            break
        except LoopContinue:
            continue


@register_action("while")
def action_while(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Repeat actions while a condition is true."""
    condition = args.get("condition", "")
    actions_data = args.get("actions", [])
    max_iterations = int(args.get("max_iterations", 1000))

    if not actions_data:
        return

    parsed = executor._parse_actions(actions_data)
    iteration = 0

    while context.evaluate_condition(condition):
        if iteration >= max_iterations:
            raise MacroExecutionError(
                f"while loop exceeded max_iterations ({max_iterations})"
            )
        iteration += 1

        try:
            executor.execute_actions(parsed, context)
        except LoopBreak:
            break
        except LoopContinue:
            continue


@register_action("foreach")
def action_foreach(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Iterate over a list."""
    items = args.get("items", [])
    loop_var = args.get("as", "item")
    index_var = args.get("index_as")
    actions_data = args.get("actions", [])

    if not actions_data or not items:
        return

    # Handle string items (comma-separated)
    if isinstance(items, str):
        items = [i.strip() for i in items.split(",")]

    parsed = executor._parse_actions(actions_data)

    for i, item in enumerate(items):
        context.set(loop_var, item)
        if index_var:
            context.set(index_var, i)

        try:
            executor.execute_actions(parsed, context)
        except LoopBreak:
            break
        except LoopContinue:
            continue


@register_action("try")
def action_try(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> Any:
    """Try/catch/finally error handling."""
    actions_data = args.get("actions", [])
    catch_data = args.get("catch", [])
    finally_data = args.get("finally", [])
    error_var = args.get("error_as", "error")

    result = None
    error_occurred = False

    try:
        if actions_data:
            parsed = executor._parse_actions(actions_data)
            result = executor.execute_actions(parsed, context)
    except (LoopBreak, LoopContinue):
        # Re-raise loop control exceptions
        raise
    except Exception as e:
        error_occurred = True
        context.set(error_var, str(e))
        if catch_data:
            parsed = executor._parse_actions(catch_data)
            result = executor.execute_actions(parsed, context)

    # Always run finally block
    if finally_data:
        parsed = executor._parse_actions(finally_data)
        executor.execute_actions(parsed, context)

    # If error occurred and no catch block, re-raise
    if error_occurred and not catch_data:
        raise MacroExecutionError(context.get(error_var, "Unknown error"))

    return result


@register_action("break")
def action_break(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Break out of a loop."""
    raise LoopBreak()


@register_action("continue")
def action_continue(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Continue to next loop iteration."""
    raise LoopContinue()


@register_action("fail")
def action_fail(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Explicitly fail with an error message."""
    message = args.get("message", "Macro execution failed")
    raise MacroExecutionError(message)


@register_action("log")
def action_log(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> None:
    """Log a message (printed to stdout if verbose, otherwise suppressed)."""
    message = args.get("message", "")
    level = args.get("level", "info")

    if executor.verbose:
        prefix = {"debug": "[DEBUG]", "info": "[INFO]", "warn": "[WARN]", "error": "[ERROR]"}.get(
            level, "[INFO]"
        )
        print(f"{prefix} {message}")


@register_action("call")
def action_call(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> Any:
    """Call another macro as a subroutine."""
    from automeister.macro.parser import find_macro

    macro_name = args.get("macro", "")
    macro_dir = args.get("directory")
    call_params = args.get("params", {})

    if not macro_name:
        raise MacroExecutionError("call action requires 'macro' argument")

    # Find the macro
    macro = find_macro(macro_name, macro_dir)
    if macro is None:
        raise MacroExecutionError(f"Macro not found: {macro_name}")

    # Create a child executor to track call depth
    child_executor = executor.create_child_executor()

    # Execute the macro with provided params
    child_executor.execute(macro, call_params)

    return None


@register_action("return")
def action_return(
    args: dict[str, Any], context: MacroContext, executor: MacroExecutor
) -> Any:
    """Return a value from a macro (for use with call)."""
    value = args.get("value")
    # Store return value in context for potential retrieval
    context.set("_return_value", value)
    return value
