# Automeister MCP Server

Automeister provides an MCP (Model Context Protocol) server that exposes desktop automation capabilities as tools for Claude Code and other MCP-compatible AI agents.

## Quick Start

### 1. Install Automeister

```bash
pip install automeister
```

Or install from source:

```bash
git clone https://github.com/automeister/automeister
cd automeister
pip install -e .
```

### 2. Configure Claude Code

Add the Automeister MCP server to your `.mcp.json` file:

```json
{
  "mcpServers": {
    "automeister": {
      "command": "automeister-mcp",
      "args": []
    }
  }
}
```

If using a virtual environment, specify the full path:

```json
{
  "mcpServers": {
    "automeister": {
      "command": "/path/to/venv/bin/automeister-mcp",
      "args": []
    }
  }
}
```

### 3. Use in Claude Code

Once configured, Claude Code will have access to the Automeister tools. You can ask Claude to:

- "Take a screenshot of the screen"
- "Click at position 500, 300"
- "Type 'Hello, World!'"
- "Focus the Firefox window"
- "Find the 'Submit' button on screen"

---

## Available Tools

### Screen Tools

#### `screen_capture`

Capture the screen or a region of it. Returns base64-encoded PNG for multimodal analysis.

| Parameter | Type | Description |
|-----------|------|-------------|
| `region_x` | int | X coordinate of region (optional) |
| `region_y` | int | Y coordinate of region (optional) |
| `region_width` | int | Width of region (optional) |
| `region_height` | int | Height of region (optional) |
| `output_path` | str | Save to file instead of returning base64 (optional) |

#### `screen_find`

Find a template image on screen using OpenCV template matching.

| Parameter | Type | Description |
|-----------|------|-------------|
| `template_path` | str | Path to template image file |
| `threshold` | float | Match confidence 0.0-1.0 (default: 0.8) |
| `region_x/y/width/height` | int | Search region (optional) |
| `grayscale` | bool | Convert to grayscale before matching |

#### `screen_ocr`

Extract text from the screen using OCR (Tesseract).

| Parameter | Type | Description |
|-----------|------|-------------|
| `region_x/y/width/height` | int | OCR region (optional) |
| `lang` | str | Language code (default: "eng") |

#### `screen_wait_for_text`

Wait for text to appear on screen via OCR.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | str | Text to wait for |
| `timeout` | float | Max wait time in seconds (default: 30) |
| `region_x/y/width/height` | int | Search region (optional) |
| `exact` | bool | Require exact word match |

---

### Mouse Tools

#### `mouse_move`

Move the mouse cursor to a position.

| Parameter | Type | Description |
|-----------|------|-------------|
| `x` | int | X coordinate |
| `y` | int | Y coordinate |
| `relative` | bool | Move relative to current position |
| `duration` | float | Animation duration in seconds |

#### `mouse_click`

Click the mouse at current position or specified coordinates.

| Parameter | Type | Description |
|-----------|------|-------------|
| `x` | int | X coordinate (optional) |
| `y` | int | Y coordinate (optional) |
| `button` | str | "left", "middle", or "right" |
| `count` | int | Number of clicks |

#### `mouse_drag`

Drag the mouse from one position to another.

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_x` | int | Starting X coordinate |
| `start_y` | int | Starting Y coordinate |
| `end_x` | int | Ending X coordinate |
| `end_y` | int | Ending Y coordinate |
| `button` | str | Button to hold during drag |
| `duration` | float | Duration in seconds |

#### `mouse_scroll`

Scroll the mouse wheel.

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | int | Scroll units (positive=down, negative=up) |
| `horizontal` | bool | Scroll horizontally |

---

### Keyboard Tools

#### `keyboard_type`

Type text using the keyboard.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | str | Text to type |
| `delay` | int | Delay between keystrokes in ms |

#### `keyboard_key`

Press a single key, optionally with modifiers.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | str | Key name (e.g., "Return", "Tab", "F1") |
| `modifiers` | list[str] | Modifiers (e.g., ["ctrl", "shift"]) |

#### `keyboard_hotkey`

Press a key combination.

| Parameter | Type | Description |
|-----------|------|-------------|
| `combo` | str | Key combination (e.g., "ctrl+c", "alt+F4") |

---

### Window Tools

#### `window_list`

List all windows, optionally filtered.

| Parameter | Type | Description |
|-----------|------|-------------|
| `title_filter` | str | Filter by title (substring match) |
| `wm_class_filter` | str | Filter by WM_CLASS |

#### `window_focus`

Focus a window (bring to front and activate).

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | str | Window title |
| `wm_class` | str | WM_CLASS |
| `window_id` | str | Window ID (hex format) |

#### `window_move`

Move a window to a position.

| Parameter | Type | Description |
|-----------|------|-------------|
| `x` | int | Target X coordinate |
| `y` | int | Target Y coordinate |
| `title/wm_class/window_id` | str | Window identifier |

#### `window_resize`

Resize a window.

| Parameter | Type | Description |
|-----------|------|-------------|
| `width` | int | Target width |
| `height` | int | Target height |
| `title/wm_class/window_id` | str | Window identifier |

#### `window_minimize` / `window_maximize` / `window_close`

Window state management.

| Parameter | Type | Description |
|-----------|------|-------------|
| `title/wm_class/window_id` | str | Window identifier |

---

### Macro Tools

#### `run_macro`

Execute an Automeister macro by name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Macro name (without .yaml) |
| `params` | dict | Parameters to pass to macro |
| `verbose` | bool | Print execution details |

---

### Utility Tools

#### `delay`

Pause execution.

| Parameter | Type | Description |
|-----------|------|-------------|
| `seconds` | float | Duration to wait |

---

## Agent Integration Patterns

The MCP server enables powerful agent-driven automation patterns:

### 1. Capture-Analyze-Act

```
1. screen_capture() -> Get current screen state
2. Claude analyzes the image (multimodal)
3. mouse_click(x, y) -> Act on analysis
4. screen_capture() -> Verify result
```

### 2. OCR-Driven Navigation

```
1. screen_ocr() -> Read all visible text
2. Find target element from text content
3. mouse_click() or keyboard_type() -> Interact
```

### 3. Template-Based Interaction

```
1. screen_find(template) -> Locate UI element
2. Use returned coordinates to click/interact
3. screen_wait_for_text() -> Verify state change
```

### 4. Error Recovery

```
1. Attempt action
2. screen_capture() -> Check for error dialogs
3. If error: keyboard_key("Escape") or window_close()
4. Retry with different approach
```

---

## System Requirements

- Linux with X11 display server
- Python 3.10+
- System dependencies:
  - `xdotool` - keyboard/mouse automation
  - `scrot` or `maim` - screen capture
  - `wmctrl` - window management
  - `tesseract-ocr` - OCR (optional)

Install on Debian/Ubuntu:

```bash
sudo apt install xdotool scrot wmctrl tesseract-ocr
```

---

## Troubleshooting

### DISPLAY not set

If tools fail with "Can't open X display", ensure `DISPLAY` is set:

```bash
export DISPLAY=:0
```

Or configure in `~/.config/automeister/config.yaml`:

```yaml
display:
  display: ":0"
```

### Permission denied

On some systems, X11 may require authentication. Ensure you're running in a graphical session or have proper Xauthority configured.

### Tool not found

Ensure system dependencies are installed. Run:

```bash
automeister check-deps
```
