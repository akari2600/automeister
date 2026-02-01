"""Macro executor for Automeister."""

from typing import Any

from automeister.actions import image, keyboard, mouse, screen, util
from automeister.macro.context import MacroContext
from automeister.macro.parser import Macro, MacroAction


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

    def __init__(self, verbose: bool = False) -> None:
        """
        Initialize the executor.

        Args:
            verbose: If True, print action details during execution
        """
        self.verbose = verbose
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
        # Validate and process parameters
        validated_params = macro.validate_params(params or {})

        # Create execution context
        context = MacroContext(params=validated_params, vars=macro.vars)

        # Execute actions
        for i, action in enumerate(macro.actions):
            self._execute_action(action, context, i)

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

        # Render arguments
        rendered_args = context.render_value(action.args)

        if self.verbose:
            print(f"Executing: {action.action} {rendered_args}")

        # Find and execute handler
        handler = ACTION_HANDLERS.get(action.action)
        if handler is None:
            raise MacroExecutionError(
                f"Unknown action: {action.action}",
                action_index=index,
                action_name=action.name,
            )

        try:
            result = handler(rendered_args, context)
            return result
        except Exception as e:
            raise MacroExecutionError(
                str(e),
                action_index=index,
                action_name=action.name,
            ) from e


# =============================================================================
# Built-in Action Handlers
# =============================================================================


@register_action("set-var")
def action_set_var(args: dict[str, Any], context: MacroContext) -> None:
    """Set a runtime variable."""
    name = args.get("name")
    value = args.get("value")
    if name is None:
        raise ValueError("set-var requires 'name' argument")
    context.set(name, value)


@register_action("delay")
def action_delay(args: dict[str, Any], context: MacroContext) -> None:
    """Pause execution."""
    seconds = args.get("seconds", args.get("duration", 1.0))
    util.delay(float(seconds))


@register_action("notify")
def action_notify(args: dict[str, Any], context: MacroContext) -> None:
    """Show a notification."""
    message = args.get("message", "")
    title = args.get("title")
    urgency = args.get("urgency")
    timeout = args.get("timeout")
    util.notify(message, title=title, urgency=urgency, timeout=timeout)


@register_action("shell")
def action_shell(args: dict[str, Any], context: MacroContext) -> str:
    """Run a shell command."""
    command = args.get("command", "")
    timeout = args.get("timeout")
    result = util.shell(command, timeout=timeout)

    # Optionally store result in a variable
    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


@register_action("clipboard.get")
def action_clipboard_get(args: dict[str, Any], context: MacroContext) -> str:
    """Get clipboard content."""
    result = util.clipboard_get()

    store_as = args.get("store_as")
    if store_as:
        context.set(store_as, result)

    return result


@register_action("clipboard.set")
def action_clipboard_set(args: dict[str, Any], context: MacroContext) -> None:
    """Set clipboard content."""
    text = args.get("text", "")
    util.clipboard_set(text)


# Mouse actions


@register_action("mouse.move")
def action_mouse_move(args: dict[str, Any], context: MacroContext) -> None:
    """Move the mouse."""
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    relative = args.get("relative", False)
    duration = args.get("duration")
    mouse.move(x, y, relative=relative, duration=duration)


@register_action("mouse.click")
def action_mouse_click(args: dict[str, Any], context: MacroContext) -> None:
    """Click the mouse."""
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    mouse.click(button=button, count=count)


@register_action("mouse.click-at")
def action_mouse_click_at(args: dict[str, Any], context: MacroContext) -> None:
    """Move and click."""
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    button = args.get("button", "left")
    count = int(args.get("count", 1))
    mouse.click_at(x, y, button=button, count=count)


@register_action("mouse.drag")
def action_mouse_drag(args: dict[str, Any], context: MacroContext) -> None:
    """Drag the mouse."""
    x1 = int(args.get("x1", args.get("from_x", 0)))
    y1 = int(args.get("y1", args.get("from_y", 0)))
    x2 = int(args.get("x2", args.get("to_x", 0)))
    y2 = int(args.get("y2", args.get("to_y", 0)))
    button = args.get("button", "left")
    duration = args.get("duration")
    mouse.drag(x1, y1, x2, y2, button=button, duration=duration)


@register_action("mouse.scroll")
def action_mouse_scroll(args: dict[str, Any], context: MacroContext) -> None:
    """Scroll the mouse wheel."""
    amount = int(args.get("amount", 3))
    horizontal = args.get("horizontal", False)
    mouse.scroll(amount, horizontal=horizontal)


@register_action("mouse.click-image")
def action_mouse_click_image(args: dict[str, Any], context: MacroContext) -> None:
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
def action_keyboard_type(args: dict[str, Any], context: MacroContext) -> None:
    """Type text."""
    text = args.get("text", "")
    delay = args.get("delay")
    keyboard.type_text(text, delay=delay)


@register_action("keyboard.key")
def action_keyboard_key(args: dict[str, Any], context: MacroContext) -> None:
    """Press a key."""
    key_name = args.get("key", "")
    modifiers = args.get("modifiers")
    if isinstance(modifiers, str):
        modifiers = [m.strip() for m in modifiers.split(",")]
    keyboard.key(key_name, modifiers=modifiers)


@register_action("keyboard.hotkey")
def action_keyboard_hotkey(args: dict[str, Any], context: MacroContext) -> None:
    """Press a key combination."""
    combo = args.get("combo", args.get("keys", ""))
    keyboard.hotkey(combo)


# Screen actions


@register_action("screen.capture")
def action_screen_capture(args: dict[str, Any], context: MacroContext) -> str:
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
def action_screen_find(args: dict[str, Any], context: MacroContext) -> dict | None:
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
def action_screen_wait_for(args: dict[str, Any], context: MacroContext) -> dict:
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
def action_screen_exists(args: dict[str, Any], context: MacroContext) -> bool:
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
