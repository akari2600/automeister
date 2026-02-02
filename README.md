# Automeister

A desktop-agnostic GUI automation framework for Linux X11, designed for AI agent integration.

## Overview

Automeister provides Keyboard Maestro-style automation capabilities on Linux without dependency on any specific desktop environment's accessibility APIs. It operates at the X11/display server level, using screen capture, image recognition, and input simulation to interact with any GUI application.

## Features

- **Desktop Agnostic**: Works on XFCE, GNOME, KDE, or any X11-based environment
- **CLI-First**: All operations accessible via command line for easy agent integration
- **Composable**: Small, focused primitives that combine into complex workflows
- **Parameterized**: Macros accept runtime parameters for dynamic behavior
- **YAML Macros**: Define complex automation workflows in simple YAML files
- **Image Recognition**: Find and click UI elements using template matching
- **OCR Support**: Extract text from screen using Tesseract
- **Window Management**: Control windows programmatically
- **JSON Output**: Machine-readable output for agent integration
- **Inspectable**: Clear logging and debugging output for troubleshooting

## Installation

### Prerequisites

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt install xdotool scrot xclip libnotify-bin

# Optional dependencies
sudo apt install maim          # Alternative screen capture
sudo apt install wmctrl        # Window management
sudo apt install tesseract-ocr # OCR support

# Install Automeister
pip install automeister
```

### Verify Installation

```bash
# Check all dependencies
automeister check
```

## Quick Start

### Direct Actions

```bash
# Take a screenshot
automeister exec screen.capture --output screenshot.png

# Move mouse and click
automeister exec mouse.move 500 300
automeister exec mouse.click

# Click at coordinates
automeister exec mouse.click-at 500 300

# Type text
automeister exec keyboard.type "Hello, World!"

# Press key combinations
automeister exec keyboard.hotkey "ctrl+s"

# Find and click an image on screen
automeister exec mouse.click-image button.png --timeout 10

# Wait for an image to appear
automeister exec screen.wait-for button.png --timeout 30

# OCR - extract text from screen
automeister exec screen.ocr --region 100,100,400,200

# Window management
automeister exec window.list
automeister exec window.focus --title "Firefox"
```

### Macros

Create a macro file at `~/.config/automeister/macros/login.yaml`:

```yaml
name: login
description: "Log in to application"

parameters:
  - name: username
    type: string
    required: true
  - name: password
    type: string
    required: true

actions:
  - action: screen.wait-for
    template: login_button.png
    timeout: 30

  - action: mouse.click-image
    template: username_field.png

  - action: keyboard.type
    text: "{{ username }}"

  - action: keyboard.key
    key: Tab

  - action: keyboard.type
    text: "{{ password }}"

  - action: keyboard.key
    key: Return
```

Run the macro:

```bash
automeister run login --param username=myuser --param password=secret
```

### Flow Control

Macros support conditionals, loops, and error handling:

```yaml
name: batch-process
description: "Process multiple files"

vars:
  files: "file1.txt,file2.txt,file3.txt"

actions:
  # Loop through files
  - action: foreach
    items: "{{ files }}"
    as: file
    actions:
      - action: log
        message: "Processing {{ file }}"

      # Try with error handling
      - action: try
        actions:
          - action: shell
            command: "process {{ file }}"
        catch:
          - action: log
            message: "Failed to process {{ file }}: {{ error }}"
            level: error

  # Conditional
  - action: if
    condition: "{{ success_count > 0 }}"
    then:
      - action: notify
        message: "Processed {{ success_count }} files"
```

## CLI Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `automeister run <macro>` | Run a macro by name or path |
| `automeister debug <macro>` | Debug a macro with verbose output |
| `automeister exec <action>` | Execute a single action |
| `automeister check` | Verify system dependencies |
| `automeister macro list` | List available macros |
| `automeister macro show <name>` | Show macro details |
| `automeister macro validate <name>` | Validate macro syntax |
| `automeister macro create <name>` | Create a new macro |

### Screen Actions

| Action | Description |
|--------|-------------|
| `screen.capture` | Capture screenshot |
| `screen.find` | Find template image on screen |
| `screen.wait-for` | Wait for image to appear |
| `screen.exists` | Check if image exists |
| `screen.ocr` | Extract text using OCR |
| `screen.find-text` | Check if text exists on screen |
| `screen.wait-for-text` | Wait for text to appear |

### Mouse Actions

| Action | Description |
|--------|-------------|
| `mouse.move` | Move cursor to position |
| `mouse.click` | Click at current position |
| `mouse.click-at` | Move and click |
| `mouse.click-image` | Find image and click it |
| `mouse.drag` | Drag from one position to another |
| `mouse.scroll` | Scroll mouse wheel |

### Keyboard Actions

| Action | Description |
|--------|-------------|
| `keyboard.type` | Type text |
| `keyboard.key` | Press a key with optional modifiers |
| `keyboard.hotkey` | Press a key combination |

### Window Actions

| Action | Description |
|--------|-------------|
| `window.list` | List open windows |
| `window.focus` | Focus a window |
| `window.move` | Move a window |
| `window.resize` | Resize a window |
| `window.minimize` | Minimize a window |
| `window.maximize` | Maximize a window |
| `window.close` | Close a window |
| `window.wait-for` | Wait for window to appear |

### Utility Actions

| Action | Description |
|--------|-------------|
| `delay` | Pause execution |
| `notify` | Show desktop notification |
| `clipboard.get` | Get clipboard content |
| `clipboard.set` | Set clipboard content |
| `shell` | Execute shell command |
| `log` | Log a message |
| `fail` | Fail with error message |

### Flow Control Actions (Macros Only)

| Action | Description |
|--------|-------------|
| `if` | Conditional execution |
| `repeat` | Repeat N times |
| `while` | Loop while condition is true |
| `foreach` | Iterate over items |
| `try` | Try/catch error handling |
| `break` | Break out of loop |
| `continue` | Continue to next iteration |
| `call` | Call another macro |

## JSON Output

Use `--json` for machine-readable output:

```bash
# Run macro with JSON output
automeister run my-macro --json

# List macros as JSON
automeister macro list --json

# Check dependencies as JSON
automeister check --json
```

## Debugging

```bash
# Debug with stepping (pause before each action)
automeister debug my-macro --step

# Validate macro syntax
automeister macro validate my-macro

# Run with verbose output
automeister run my-macro --verbose
```

## Configuration

Configuration file: `~/.config/automeister/config.yaml`

```yaml
display:
  number: 0           # X display number

capture:
  tool: scrot         # scrot or maim

timeouts:
  default: 30.0       # Default timeout in seconds
  command: 60.0       # Shell command timeout

mouse:
  move_duration: 0.0  # Mouse move animation duration

keyboard:
  type_delay: 0.0     # Delay between keystrokes
```

## Project Status

All core phases are complete:

- ✅ Phase 1: Core Foundation
- ✅ Phase 2: Image Recognition
- ✅ Phase 3: Macro System
- ✅ Phase 4: Flow Control
- ✅ Phase 5: Advanced Features
- ✅ Phase 6: Polish

## License

MIT License - see [LICENSE](LICENSE) for details.
