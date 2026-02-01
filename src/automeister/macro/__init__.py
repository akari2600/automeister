"""Macro system for Automeister."""

from automeister.macro.context import MacroContext
from automeister.macro.executor import MacroExecutor
from automeister.macro.parser import (
    Macro,
    MacroAction,
    MacroParameter,
    find_macro,
    get_macros_dir,
    load_macro,
    load_macros,
)

__all__ = [
    "Macro",
    "MacroAction",
    "MacroContext",
    "MacroExecutor",
    "MacroParameter",
    "find_macro",
    "get_macros_dir",
    "load_macro",
    "load_macros",
]
