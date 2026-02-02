# Automeister CLI Reference

## Global Options

```bash
automeister [--json] [--verbose] [--config <path>] <command>
```

| Option | Description |
|--------|-------------|
| `--json` | Output results as JSON |
| `--verbose` | Enable verbose logging |
| `--config` | Path to config file (default: `~/.config/automeister/config.yaml`) |

---

## Macro Commands

### `automeister macro list`

List all available macros.

```bash
automeister macro list
```

### `automeister macro show <name>`

Display macro details.

```bash
automeister macro show login_workflow
```

### `automeister macro create <name>`

Create a new macro (opens editor).

```bash
automeister macro create my_macro
```

### `automeister macro edit <name>`

Edit an existing macro.

```bash
automeister macro edit my_macro
```

### `automeister macro delete <name>`

Delete a macro.

```bash
automeister macro delete my_macro
```

### `automeister macro export <name>`

Export macro to file.

```bash
automeister macro export my_macro --output my_macro.yaml
```

### `automeister macro import <file>`

Import macro from file.

```bash
automeister macro import my_macro.yaml
```

---

## Execution Commands

### `automeister run <macro-name>`

Execute a macro.

```bash
# Basic execution
automeister run login_workflow

# With parameters
automeister run login_workflow --param username=test --param count=5

# Parameters from JSON file
automeister run login_workflow --params-file params.json
```

### `automeister debug <macro-name>`

Debug macro execution.

```bash
# Step-by-step execution
automeister debug login_workflow --step

# Verbose output
automeister debug login_workflow --verbose
```

### `automeister validate <macro-name>`

Validate macro syntax without executing.

```bash
automeister validate login_workflow
```

---

## Direct Action Commands

Execute actions directly without macros using `automeister exec`.

### Screen Actions

#### `screen.capture`

Capture screenshot.

```bash
# Full screen
automeister exec screen.capture --output screenshot.png

# Region capture
automeister exec screen.capture --region 0,0,800,600 --output region.png
```

| Option | Description |
|--------|-------------|
| `--output <file>` | Output file path |
| `--region <x,y,w,h>` | Capture region |

#### `screen.find`

Find image on screen.

```bash
automeister exec screen.find button.png --threshold 0.8
```

| Option | Description |
|--------|-------------|
| `--threshold <0.0-1.0>` | Match confidence (default: 0.8) |
| `--region <x,y,w,h>` | Search region |
| `--grayscale` | Convert to grayscale |

#### `screen.ocr`

Extract text from screen.

```bash
# Full screen
automeister exec screen.ocr

# Region
automeister exec screen.ocr --region 100,100,400,50 --lang eng
```

| Option | Description |
|--------|-------------|
| `--region <x,y,w,h>` | OCR region |
| `--lang <code>` | Language (default: eng) |

#### `screen.wait-for-image`

Wait for image to appear.

```bash
automeister exec screen.wait-for-image button.png --timeout 30
```

| Option | Description |
|--------|-------------|
| `--timeout <seconds>` | Max wait time (default: 30) |
| `--threshold <0.0-1.0>` | Match confidence |
| `--region <x,y,w,h>` | Search region |

#### `screen.wait-for-text`

Wait for text to appear via OCR.

```bash
automeister exec screen.wait-for-text "Login successful" --timeout 30
```

| Option | Description |
|--------|-------------|
| `--timeout <seconds>` | Max wait time (default: 30) |
| `--region <x,y,w,h>` | Search region |
| `--exact` | Exact match (default: substring) |

---

### Mouse Actions

#### `mouse.move`

Move cursor.

```bash
# Absolute position
automeister exec mouse.move 500 300

# Relative movement
automeister exec mouse.move 100 50 --relative

# Smooth movement
automeister exec mouse.move 500 300 --duration 0.5
```

| Option | Description |
|--------|-------------|
| `--relative` | Move relative to current position |
| `--duration <seconds>` | Movement duration (0 = instant) |

#### `mouse.click`

Click at current position.

```bash
# Left click
automeister exec mouse.click

# Right click
automeister exec mouse.click --button right

# Double click
automeister exec mouse.click --count 2
```

| Option | Description |
|--------|-------------|
| `--button <left\|right\|middle>` | Button (default: left) |
| `--count <n>` | Click count (default: 1) |

#### `mouse.click-at`

Move and click.

```bash
automeister exec mouse.click-at 500 300 --button left
```

#### `mouse.click-image`

Find image and click it.

```bash
automeister exec mouse.click-image button.png --offset 0,10
```

| Option | Description |
|--------|-------------|
| `--button <left\|right\|middle>` | Button (default: left) |
| `--offset <x,y>` | Click offset from center |
| `--threshold <0.0-1.0>` | Match confidence |
| `--timeout <seconds>` | Max wait time |

#### `mouse.drag`

Drag from one point to another.

```bash
automeister exec mouse.drag 100 100 500 500 --duration 0.5
```

| Option | Description |
|--------|-------------|
| `--button <left\|right\|middle>` | Button (default: left) |
| `--duration <seconds>` | Drag duration |

#### `mouse.scroll`

Scroll wheel.

```bash
# Scroll up
automeister exec mouse.scroll 3

# Scroll down
automeister exec mouse.scroll -3

# Horizontal scroll
automeister exec mouse.scroll 3 --horizontal
```

| Option | Description |
|--------|-------------|
| `--horizontal` | Scroll horizontally |

---

### Keyboard Actions

#### `keyboard.type`

Type text.

```bash
automeister exec keyboard.type "Hello, World!"

# With delay between characters
automeister exec keyboard.type "slow typing" --delay 0.1
```

| Option | Description |
|--------|-------------|
| `--delay <seconds>` | Delay between characters |

#### `keyboard.key`

Press a single key.

```bash
# Simple key
automeister exec keyboard.key Return

# With modifiers
automeister exec keyboard.key c --modifiers ctrl
```

| Option | Description |
|--------|-------------|
| `--modifiers <mod1,mod2>` | Modifiers: ctrl, alt, shift, super |

#### `keyboard.hotkey`

Press key combination.

```bash
automeister exec keyboard.hotkey "ctrl+shift+t"
automeister exec keyboard.hotkey "alt+F4"
```

---

### Window Actions

#### `window.list`

List windows.

```bash
# All windows
automeister exec window.list

# Filtered
automeister exec window.list --filter "Firefox"
```

#### `window.focus`

Focus a window.

```bash
# By name
automeister exec window.focus "Firefox"

# By ID
automeister exec window.focus 0x12345678
```

#### `window.move`

Move a window.

```bash
automeister exec window.move "Firefox" 100 100
```

> **Note:** Maximized windows may not respond to move commands. Use `window.restore` to unmaximize first.

#### `window.resize`

Resize a window.

```bash
automeister exec window.resize "Firefox" 1280 720
```

> **Note:** Maximized windows may not respond to resize commands. Use `window.restore` to unmaximize first.

#### `window.minimize` / `window.maximize` / `window.restore` / `window.close`

Window state changes.

```bash
automeister exec window.minimize "Firefox"
automeister exec window.maximize "Firefox"
automeister exec window.restore "Firefox"   # Unmaximize
automeister exec window.close "Firefox"
```

#### `window.wait-for`

Wait for window to appear.

```bash
automeister exec window.wait-for "Save As" --timeout 10
```

---

### Utility Actions

#### `delay`

Pause execution.

```bash
automeister exec delay 2.5
```

#### `notify`

Show desktop notification.

```bash
automeister exec notify "Task completed" --title "Automeister"
```

#### `clipboard.get` / `clipboard.set`

Clipboard operations.

```bash
# Get clipboard content
automeister exec clipboard.get

# Set clipboard content
automeister exec clipboard.set "Hello, clipboard!"
```

#### `shell`

Execute shell command.

```bash
automeister exec shell "echo Hello"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Macro not found |
| 4 | Template image not found |
| 5 | Screen element not found (timeout) |
| 6 | Window not found |
| 7 | Action failed |
| 8 | Parameter validation failed |
| 9 | Dependency missing |

## JSON Output

With `--json`, all commands output structured JSON:

```json
{
  "success": true,
  "result": {
    "x": 450,
    "y": 320,
    "confidence": 0.95
  }
}
```

Error format:

```json
{
  "success": false,
  "error": {
    "code": 5,
    "type": "ElementNotFound",
    "message": "Timeout waiting for image 'button.png'"
  }
}
```
