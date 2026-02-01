# Automeister Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
│                     (automeister command)                    │
├─────────────────────────────────────────────────────────────┤
│                      Macro Engine                            │
│            (CRUD, execution, parameter binding)              │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Screen     │    Input     │   Window     │    Flow        │
│   Module     │   Module     │   Module     │   Control      │
├──────────────┼──────────────┼──────────────┼────────────────┤
│  - capture   │  - mouse     │  - list      │  - conditions  │
│  - find      │  - keyboard  │  - focus     │  - loops       │
│  - ocr       │  - type      │  - move      │  - variables   │
│  - wait      │  - click     │  - resize    │  - delays      │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   System Layer    │
                    │  xdotool, scrot,  │
                    │  tesseract, etc.  │
                    └───────────────────┘
```

## Component Details

### CLI Interface

The command-line interface is built with [Typer](https://typer.tiangolo.com/), providing:

- `automeister exec <action>` - Direct action execution
- `automeister run <macro>` - Macro execution
- `automeister macro <command>` - Macro management
- `automeister debug <macro>` - Debugging tools

### Macro Engine

Responsible for:

- Loading and parsing YAML macro definitions
- Parameter validation and binding
- Variable resolution and expression evaluation
- Action sequencing and execution
- Error handling and recovery

### Screen Module

Handles all screen-related operations:

| Function | Backend | Description |
|----------|---------|-------------|
| `capture` | scrot/maim | Screenshot capture |
| `find` | OpenCV | Template matching |
| `ocr` | Tesseract | Text extraction |
| `wait_for_image` | OpenCV | Polling for image |
| `wait_for_text` | Tesseract | Polling for text |

### Input Module

Handles mouse and keyboard input via xdotool:

| Function | xdotool Command | Description |
|----------|-----------------|-------------|
| `mouse.move` | `mousemove` | Move cursor |
| `mouse.click` | `click` | Mouse click |
| `mouse.drag` | `mousedown`/`mouseup` | Drag operation |
| `mouse.scroll` | `click 4/5` | Scroll wheel |
| `keyboard.type` | `type` | Type text |
| `keyboard.key` | `key` | Press key |

### Window Module

Window management via wmctrl:

| Function | wmctrl Command | Description |
|----------|----------------|-------------|
| `list` | `wmctrl -l -G` | List windows |
| `focus` | `wmctrl -a` | Focus window |
| `move` | `wmctrl -r -e` | Move window |
| `resize` | `wmctrl -r -e` | Resize window |

### Flow Control

Control flow constructs executed by the macro engine:

- **Conditionals**: `if`/`then`/`else` with expression evaluation
- **Loops**: `repeat`, `while`, `foreach`
- **Error Handling**: `try`/`catch`
- **Variables**: `set-var`, expression interpolation

## Directory Structure

```
~/.config/automeister/
├── config.yaml           # Global configuration
├── macros/               # Macro definitions
│   ├── example.yaml
│   └── login_workflow.yaml
├── templates/            # Image templates for matching
│   ├── buttons/
│   │   ├── submit.png
│   │   └── cancel.png
│   └── dialogs/
│       └── error.png
├── logs/                 # Execution logs
│   └── 2024-01-15.log
└── temp/                 # Temporary files
```

## Data Flow

### Direct Action Execution

```
User -> CLI -> Action Module -> System Tool -> Result -> CLI -> User
```

### Macro Execution

```
User -> CLI -> Macro Engine -> Load YAML
                           -> Bind Parameters
                           -> For each action:
                              -> Evaluate expressions
                              -> Execute action
                              -> Handle result/errors
                           -> Return result -> CLI -> User
```

## External Dependencies

### Required

| Package | Purpose | Debian Package |
|---------|---------|----------------|
| xdotool | Input simulation | `xdotool` |
| scrot | Screenshots | `scrot` |
| OpenCV | Image matching | `python3-opencv` |
| Tesseract | OCR | `tesseract-ocr` |
| wmctrl | Window management | `wmctrl` |

### Optional

| Package | Purpose | Debian Package |
|---------|---------|----------------|
| maim | Alternative screenshots | `maim` |
| ydotool | Wayland input | `ydotool` |

## Error Handling Strategy

1. **Validation Errors**: Caught at parse/bind time, reported with context
2. **Execution Errors**: Wrapped with action index and parameters
3. **System Errors**: Tool failures mapped to specific exit codes
4. **Timeout Errors**: Configurable timeouts with clear messaging

## Notes

- Macros have full access to shell commands and the display - treat them like scripts
- For sensitive operations, consider environment variables over hardcoded values
