# Automeister Technical Specification

Version: 1.0-draft

## 1. Overview

Automeister is a desktop-agnostic GUI automation framework for Linux that provides Keyboard Maestro-style automation capabilities without dependency on any specific desktop environment's accessibility APIs. It operates at the X11/display server level, using screen capture, image recognition, and input simulation.

### 1.1 Design Principles

1. **Desktop Agnostic**: Works on XFCE, GNOME, KDE, or any X11-based environment
2. **CLI-First**: All operations accessible via command line for easy agent integration
3. **Composable**: Small, focused primitives that combine into complex workflows
4. **Parameterized**: Macros accept runtime parameters for dynamic behavior
5. **Inspectable**: Clear logging and debugging output for troubleshooting

### 1.2 Target Users

- AI agents requiring GUI automation capabilities
- Developers automating repetitive GUI tasks
- QA engineers for UI testing
- System administrators for desktop automation

## 2. System Requirements

### 2.1 Required Packages

```bash
# Core input simulation
sudo apt install xdotool

# Screenshot capture
sudo apt install scrot maim

# Image processing
sudo apt install imagemagick

# OCR
sudo apt install tesseract-ocr tesseract-ocr-eng

# Window management
sudo apt install wmctrl xwininfo xprop

# Python runtime
sudo apt install python3 python3-pip python3-venv
```

### 2.2 Python Dependencies

```
typer>=0.9.0
pyyaml>=6.0
pillow>=10.0.0
opencv-python-headless>=4.8.0
numpy>=1.24.0
jinja2>=3.1.0
```

### 2.3 Optional Packages

```bash
# Additional OCR languages
sudo apt install tesseract-ocr-jpn tesseract-ocr-chi-sim

# For Wayland compatibility (future)
sudo apt install ydotool wl-clipboard grim
```

## 3. Module Specifications

### 3.1 Screen Module

#### 3.1.1 screen.capture

Captures a screenshot of the entire screen or a region.

```python
def capture(
    region: Optional[Tuple[int, int, int, int]] = None,  # x, y, width, height
    output: Optional[str] = None,  # File path, or None for temp file
    display: str = ":0"  # X display
) -> str:  # Returns path to captured image
```

**Implementation**: Uses `scrot` or `maim` based on configuration.

**Backend Commands**:
- scrot: `scrot -a x,y,w,h output.png`
- maim: `maim -g wxh+x+y output.png`

#### 3.1.2 screen.find

Locates an image template on screen using OpenCV template matching.

```python
def find(
    template: str,  # Path to template image
    threshold: float = 0.8,  # Match confidence threshold (0.0-1.0)
    region: Optional[Tuple[int, int, int, int]] = None,  # Search region
    grayscale: bool = False,  # Convert to grayscale before matching
    match: str = "best"  # best, first, all
) -> Optional[Dict]:  # {x, y, width, height, confidence} or None
```

**Implementation**:
1. Capture screenshot (or region)
2. Load template image
3. Apply `cv2.matchTemplate()` with `TM_CCOEFF_NORMED`
4. Filter results by threshold
5. Return location(s) based on `match` parameter

#### 3.1.3 screen.ocr

Extracts text from screen region using Tesseract.

```python
def ocr(
    region: Optional[Tuple[int, int, int, int]] = None,
    lang: str = "eng",
    config: str = ""  # Additional Tesseract config
) -> str:  # Extracted text
```

**Implementation**:
1. Capture screenshot (or region)
2. Run `tesseract <image> stdout -l <lang> <config>`
3. Return extracted text

#### 3.1.4 screen.wait_for_image

Polls for an image to appear on screen.

```python
def wait_for_image(
    template: str,
    timeout: float = 30.0,
    interval: float = 0.5,
    threshold: float = 0.8,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Optional[Dict]:  # Location if found, None if timeout
```

#### 3.1.5 screen.wait_for_text

Polls for text to appear on screen via OCR.

```python
def wait_for_text(
    text: str,
    timeout: float = 30.0,
    interval: float = 1.0,
    region: Optional[Tuple[int, int, int, int]] = None,
    exact: bool = False  # False = substring match
) -> bool:
```

### 3.2 Input Module

#### 3.2.1 mouse.move

```python
def move(
    x: int,
    y: int,
    relative: bool = False,
    duration: float = 0.0  # 0 = instant
) -> None:
```

**Implementation**: `xdotool mousemove [--relative] x y`

For smooth movement with duration > 0, interpolate positions over time.

#### 3.2.2 mouse.click

```python
def click(
    button: str = "left",  # left, right, middle
    count: int = 1,
    x: Optional[int] = None,  # If provided, move first
    y: Optional[int] = None
) -> None:
```

**Implementation**: `xdotool click [--repeat count] button_num`

Button mapping: left=1, middle=2, right=3

#### 3.2.3 mouse.click_image

```python
def click_image(
    template: str,
    button: str = "left",
    offset: Tuple[int, int] = (0, 0),
    threshold: float = 0.8,
    timeout: float = 10.0,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Dict:  # Location that was clicked
```

**Implementation**: Combines `screen.wait_for_image` + `mouse.click`.

#### 3.2.4 mouse.drag

```python
def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.5
) -> None:
```

**Implementation**:
```bash
xdotool mousemove start_x start_y
xdotool mousedown button_num
xdotool mousemove end_x end_y
xdotool mouseup button_num
```

#### 3.2.5 mouse.scroll

```python
def scroll(
    amount: int,  # Positive = up, negative = down
    horizontal: bool = False
) -> None:
```

**Implementation**:
- Vertical: `xdotool click 4` (up) or `click 5` (down)
- Horizontal: `xdotool click 6` (left) or `click 7` (right)

#### 3.2.6 keyboard.type

```python
def type(
    text: str,
    delay: float = 0.0  # Delay between characters in seconds
) -> None:
```

**Implementation**: `xdotool type [--delay ms] text`

#### 3.2.7 keyboard.key

```python
def key(
    key: str,  # Key name (Return, Tab, Escape, F1, etc.)
    modifiers: List[str] = []  # ctrl, alt, shift, super
) -> None:
```

**Implementation**: `xdotool key [modifier+]keyname`

#### 3.2.8 keyboard.hotkey

```python
def hotkey(
    combo: str  # e.g., "ctrl+shift+t"
) -> None:
```

**Implementation**: Parse combo string, then `xdotool key combo`

### 3.3 Window Module

#### 3.3.1 window.list

```python
def list(
    filter: Optional[str] = None  # Regex pattern for window name
) -> List[Dict]:  # [{id, name, class, x, y, width, height}, ...]
```

**Implementation**: Parse output of `wmctrl -l -G`

#### 3.3.2 window.focus

```python
def focus(
    window: str  # Window ID (hex) or name pattern
) -> bool:
```

**Implementation**:
- By name: `wmctrl -a name`
- By ID: `wmctrl -i -a id`

#### 3.3.3 window.move

```python
def move(
    window: str,
    x: int,
    y: int
) -> bool:
```

**Implementation**: `wmctrl -r window -e 0,x,y,-1,-1`

#### 3.3.4 window.resize

```python
def resize(
    window: str,
    width: int,
    height: int
) -> bool:
```

**Implementation**: `wmctrl -r window -e 0,-1,-1,width,height`

#### 3.3.5 window.wait_for

```python
def wait_for(
    name: str,  # Window name pattern
    timeout: float = 30.0,
    interval: float = 0.5
) -> Optional[Dict]:  # Window info if found
```

### 3.4 Flow Control

#### 3.4.1 delay

```python
def delay(seconds: float) -> None:
```

#### 3.4.2 set_var

```python
def set_var(name: str, value: Any) -> None:
```

#### 3.4.3 log

```python
def log(
    message: str,
    level: str = "info"  # debug, info, warning, error
) -> None:
```

#### 3.4.4 fail

```python
def fail(message: str) -> None:
    """Immediately terminate macro with error."""
```

#### 3.4.5 shell

```python
def shell(
    command: str,
    timeout: float = 30.0,
    capture: bool = True
) -> Dict:  # {stdout, stderr, returncode}
```

## 4. Macro Definition Format

Macros are stored as YAML files in `~/.config/automeister/macros/`.

### 4.1 Basic Structure

```yaml
name: example
description: An example macro
version: 1

params:
  username:
    type: string
    required: true
    description: The username to enter

  click_count:
    type: integer
    default: 1
    description: Number of times to click

vars:
  timestamp: "{{ shell('date +%Y%m%d_%H%M%S') }}"
  screenshot_dir: "/tmp/automeister"

actions:
  - action: screen.wait-for-image
    template: login_button.png
    timeout: 30

  - action: mouse.click-image
    template: login_button.png

  - action: keyboard.type
    text: "{{ params.username }}"
```

### 4.2 Parameter Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `"hello"` |
| `integer` | Whole number | `42` |
| `float` | Decimal number | `3.14` |
| `boolean` | True/false | `true` |
| `list` | Array of values | `["a", "b", "c"]` |

### 4.3 Control Flow

```yaml
actions:
  # Conditional
  - action: if
    condition: "{{ screen.find('error.png') }}"
    then:
      - action: fail
        message: "Error dialog detected"
    else:
      - action: log
        message: "No error, continuing"

  # Fixed-count loop
  - action: repeat
    count: 5
    actions:
      - action: mouse.click
      - action: delay
        seconds: 0.2

  # Condition-based loop
  - action: while
    condition: "{{ not screen.find('done.png') }}"
    max_iterations: 100
    actions:
      - action: mouse.click-image
        template: next.png
      - action: delay
        seconds: 1

  # Iterate over list
  - action: foreach
    items: "{{ params.file_list }}"
    as: file
    actions:
      - action: keyboard.type
        text: "{{ file }}"

  # Error handling
  - action: try
    actions:
      - action: mouse.click-image
        template: submit.png
        timeout: 5
    catch:
      - action: mouse.click-image
        template: submit_alt.png
```

### 4.4 Expression System

Expressions use Jinja2 syntax:

```yaml
# Variable access
text: "{{ params.username }}"
text: "{{ vars.full_url }}"
text: "{{ env.API_KEY }}"

# Shell command
value: "{{ shell('date +%Y-%m-%d') }}"

# Screen state
condition: "{{ screen.find('button.png') }}"
condition: "{{ screen.ocr_contains('Success') }}"

# String filters
text: "{{ params.name | upper }}"
text: "{{ params.name | lower }}"

# Arithmetic
x: "{{ vars.center_x + 100 }}"

# Boolean
condition: "{{ params.enabled and not vars.skip }}"
```

## 5. Configuration

### 5.1 Global Configuration

```yaml
# ~/.config/automeister/config.yaml
general:
  log_level: info
  log_file: ~/.config/automeister/logs/automeister.log
  temp_dir: ~/.config/automeister/temp

screen:
  default_display: ":0"
  capture_tool: scrot  # or maim

matching:
  default_threshold: 0.8
  default_grayscale: false

input:
  type_delay: 0.0
  mouse_move_duration: 0.0

ocr:
  default_language: eng
  tesseract_path: /usr/bin/tesseract

timeouts:
  default_wait: 30.0
  default_retry_interval: 0.5
```

## 6. Error Handling

### 6.1 Exit Codes

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

### 6.2 Error Output Format (JSON)

```json
{
  "success": false,
  "error": {
    "code": 5,
    "type": "ElementNotFound",
    "message": "Timeout waiting for image 'submit_button.png'",
    "action": "screen.wait-for-image",
    "action_index": 3,
    "context": {
      "timeout": 30,
      "elapsed": 30.05,
      "template": "submit_button.png"
    }
  },
  "execution": {
    "macro": "login_workflow",
    "started_at": "2024-01-15T10:30:00Z",
    "failed_at": "2024-01-15T10:30:30Z",
    "actions_completed": 2
  }
}
```

## 7. Future Considerations

### 8.1 Wayland Support

- Input: `ydotool` instead of `xdotool`
- Screenshots: `grim` instead of `scrot`/`maim`
- Window management: Compositor-specific protocols

### 8.2 Potential Features

- Record mode (watch user actions, generate macro)
- Visual macro editor (optional GUI)
- Macro sharing/export format
- Encrypted parameter storage for secrets
- Multi-monitor support
- Image diff/change detection
