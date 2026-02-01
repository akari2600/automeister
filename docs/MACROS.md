# Automeister Macro Guide

This guide covers writing, managing, and debugging macros in Automeister.

## Macro Basics

Macros are YAML files stored in `~/.config/automeister/macros/`. Each macro defines a sequence of automated actions that can be executed with parameters.

### Minimal Macro

```yaml
name: hello
description: A simple macro that types "Hello, World!"

actions:
  - action: keyboard.type
    text: "Hello, World!"
```

Save as `~/.config/automeister/macros/hello.yaml` and run:

```bash
automeister run hello
```

## Macro Structure

### Complete Example

```yaml
# Macro metadata
name: login_workflow
description: Automates login to a web application
version: 1

# Parameter definitions
params:
  username:
    type: string
    required: true
    description: Login username

  password:
    type: string
    required: true
    description: Login password

  remember_me:
    type: boolean
    default: false
    description: Check "Remember Me" checkbox

# Computed variables
vars:
  timestamp: "{{ shell('date +%Y%m%d_%H%M%S') }}"
  log_prefix: "[{{ params.username }}]"

# Action sequence
actions:
  - action: log
    message: "{{ vars.log_prefix }} Starting login..."

  - action: screen.wait-for-image
    template: login_form.png
    timeout: 30

  - action: mouse.click-image
    template: username_field.png

  - action: keyboard.type
    text: "{{ params.username }}"

  - action: keyboard.key
    key: Tab

  - action: keyboard.type
    text: "{{ params.password }}"

  - action: if
    condition: "{{ params.remember_me }}"
    then:
      - action: mouse.click-image
        template: remember_checkbox.png

  - action: mouse.click-image
    template: login_button.png

  - action: screen.wait-for-image
    template: dashboard.png
    timeout: 30

  - action: log
    message: "{{ vars.log_prefix }} Login successful!"
```

## Parameters

### Parameter Types

| Type | Description | Example Values |
|------|-------------|----------------|
| `string` | Text | `"hello"`, `"user@example.com"` |
| `integer` | Whole number | `1`, `42`, `-5` |
| `float` | Decimal number | `3.14`, `0.5` |
| `boolean` | True/false | `true`, `false` |
| `list` | Array | `["a", "b", "c"]` |

### Parameter Options

```yaml
params:
  required_param:
    type: string
    required: true  # Must be provided
    description: This parameter is required

  optional_param:
    type: integer
    default: 10  # Used if not provided
    description: This parameter has a default

  validated_param:
    type: string
    required: true
    pattern: "^[a-z]+$"  # Regex validation
    description: Must be lowercase letters only
```

### Passing Parameters

```bash
# Command line
automeister run my_macro --param username=test --param count=5

# From JSON file
automeister run my_macro --params-file params.json
```

params.json:
```json
{
  "username": "test",
  "count": 5
}
```

## Variables

### Static Variables

```yaml
vars:
  base_url: "https://example.com"
  max_retries: 3
```

### Dynamic Variables

```yaml
vars:
  # Environment variable
  api_key: "{{ env.API_KEY }}"

  # Shell command output
  current_date: "{{ shell('date +%Y-%m-%d') }}"
  hostname: "{{ shell('hostname') }}"

  # Computed from other vars/params
  full_url: "{{ vars.base_url }}/users/{{ params.username }}"
```

### Runtime Variables

Set variables during execution:

```yaml
actions:
  - action: set-var
    name: button_location
    value: "{{ screen.find('button.png') }}"

  - action: if
    condition: "{{ vars.button_location != null }}"
    then:
      - action: mouse.click-at
        x: "{{ vars.button_location.x }}"
        y: "{{ vars.button_location.y }}"
```

## Control Flow

### Conditionals

```yaml
# Basic if
- action: if
  condition: "{{ params.debug }}"
  then:
    - action: log
      message: "Debug mode enabled"

# If/else
- action: if
  condition: "{{ screen.find('error.png') }}"
  then:
    - action: fail
      message: "Error detected!"
  else:
    - action: log
      message: "No errors found"

# Complex conditions
- action: if
  condition: "{{ params.count > 0 and not vars.skip }}"
  then:
    - action: log
      message: "Processing..."
```

### Loops

#### Fixed Count (repeat)

```yaml
- action: repeat
  count: 5
  actions:
    - action: mouse.click
    - action: delay
      seconds: 0.2
```

Access loop index:
```yaml
- action: repeat
  count: 3
  as: i
  actions:
    - action: log
      message: "Iteration {{ i }}"  # 0, 1, 2
```

#### Condition-Based (while)

```yaml
- action: while
  condition: "{{ not screen.find('complete.png') }}"
  max_iterations: 100  # Safety limit
  actions:
    - action: mouse.click-image
      template: next_button.png
    - action: delay
      seconds: 1
```

#### List Iteration (foreach)

```yaml
- action: foreach
  items: "{{ params.files }}"
  as: file
  actions:
    - action: keyboard.type
      text: "{{ file }}"
    - action: keyboard.key
      key: Return
```

With index:
```yaml
- action: foreach
  items: ["apple", "banana", "cherry"]
  as: fruit
  index_as: idx
  actions:
    - action: log
      message: "{{ idx }}: {{ fruit }}"
```

### Error Handling

```yaml
- action: try
  actions:
    - action: mouse.click-image
      template: primary_button.png
      timeout: 5
  catch:
    - action: log
      level: warning
      message: "Primary button not found, trying fallback"
    - action: mouse.click-image
      template: fallback_button.png
```

Access error info in catch:
```yaml
- action: try
  actions:
    - action: screen.wait-for-image
      template: nonexistent.png
      timeout: 5
  catch:
    - action: log
      message: "Error: {{ error.message }}"
    - action: log
      message: "Error type: {{ error.type }}"
```

## Actions Reference

### Screen Actions

```yaml
# Capture screenshot
- action: screen.capture
  output: /tmp/screenshot.png
  region: [0, 0, 800, 600]  # Optional

# Find image
- action: screen.find
  template: button.png
  threshold: 0.8
  grayscale: false
  store_result: found_location  # Store in variable

# OCR
- action: screen.ocr
  region: [100, 100, 400, 50]
  lang: eng
  store_result: extracted_text

# Wait for image
- action: screen.wait-for-image
  template: loading_complete.png
  timeout: 60
  threshold: 0.8

# Wait for text
- action: screen.wait-for-text
  text: "Success"
  timeout: 30
  exact: false  # Substring match
```

### Mouse Actions

```yaml
# Move cursor
- action: mouse.move
  x: 500
  y: 300
  relative: false
  duration: 0.5

# Click
- action: mouse.click
  button: left  # left, right, middle
  count: 1

# Click at position
- action: mouse.click-at
  x: 500
  y: 300
  button: left

# Click on image
- action: mouse.click-image
  template: button.png
  button: left
  offset: [0, 10]  # Offset from center
  threshold: 0.8
  timeout: 10

# Drag
- action: mouse.drag
  from: [100, 100]
  to: [500, 500]
  duration: 0.5

# Scroll
- action: mouse.scroll
  amount: 3  # Positive=up, negative=down
  horizontal: false
```

### Keyboard Actions

```yaml
# Type text
- action: keyboard.type
  text: "Hello, World!"
  delay: 0.05  # Delay between characters

# Press key
- action: keyboard.key
  key: Return
  modifiers: []  # ctrl, alt, shift, super

# Key with modifiers
- action: keyboard.key
  key: s
  modifiers: [ctrl]

# Hotkey combo
- action: keyboard.hotkey
  combo: "ctrl+shift+t"
```

### Window Actions

```yaml
# List windows
- action: window.list
  filter: "Firefox"
  store_result: windows

# Focus window
- action: window.focus
  window: "Firefox"

# Move window
- action: window.move
  window: "Firefox"
  x: 100
  y: 100

# Resize window
- action: window.resize
  window: "Firefox"
  width: 1280
  height: 720

# Wait for window
- action: window.wait-for
  name: "Save As"
  timeout: 10
```

### Utility Actions

```yaml
# Delay
- action: delay
  seconds: 2.5

# Log
- action: log
  message: "Processing step 3..."
  level: info  # debug, info, warning, error

# Notify
- action: notify
  message: "Task completed!"
  title: "Automeister"

# Clipboard
- action: clipboard.get
  store_result: clipboard_content

- action: clipboard.set
  text: "Copied text"

# Shell command
- action: shell
  command: "echo 'Hello'"
  timeout: 30
  store_result: shell_output

# Fail macro
- action: fail
  message: "Critical error occurred"
```

## Template Images

Store template images in `~/.config/automeister/templates/`:

```
~/.config/automeister/templates/
├── buttons/
│   ├── submit.png
│   └── cancel.png
├── dialogs/
│   ├── confirm.png
│   └── error.png
└── forms/
    └── login.png
```

Reference in macros:
```yaml
- action: mouse.click-image
  template: buttons/submit.png
```

### Capturing Templates

```bash
# Capture region for template
automeister exec screen.capture --region 100,200,150,40 --output ~/.config/automeister/templates/my_button.png
```

Tips for good templates:
- Capture only the unique part of the UI element
- Avoid capturing text that might change
- Use consistent scaling/resolution
- Test with different threshold values

## Debugging

### Validate Syntax

```bash
automeister validate my_macro
```

### Step-by-Step Execution

```bash
automeister debug my_macro --step
```

Press Enter to execute each action.

### Verbose Output

```bash
automeister debug my_macro --verbose
```

Shows:
- Parameter values
- Variable states
- Action results
- Timing information

### Common Issues

1. **Image not found**: Lower threshold or recapture template
2. **Timing issues**: Add delays between actions
3. **Wrong window focused**: Use `window.focus` before input actions
4. **OCR errors**: Capture cleaner region, try different languages

## Best Practices

1. **Use descriptive names**: `login_workflow` not `macro1`
2. **Add descriptions**: Document what each macro does
3. **Handle errors**: Use try/catch for unreliable operations
4. **Add delays**: UI needs time to respond
5. **Use variables**: Don't hardcode values
6. **Log progress**: Help debug failures
7. **Test incrementally**: Build macros step by step
8. **Version templates**: Update when UI changes
