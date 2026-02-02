# Agent Guide: Using Automeister with AI Agents

This guide covers patterns and best practices for using Automeister with AI agents like Claude Code. Whether using the CLI with `--json` output or the MCP server, these patterns will help you build reliable automation.

---

## Quick Start for Agents

### Basic Workflow: Capture → Analyze → Act → Verify

The fundamental pattern for agent-driven automation:

```
1. CAPTURE: Get current screen state
2. ANALYZE: Understand what you see
3. ACT: Perform the action
4. VERIFY: Confirm the action succeeded
```

**Example: Clicking a Button**

```bash
# 1. Capture the screen
automeister exec screen.capture --output /tmp/before.png --json

# 2. Agent analyzes the image to find button location
# (Claude uses multimodal vision to identify coordinates)

# 3. Click the button
automeister exec mouse.click-at 450 320 --json

# 4. Verify by capturing again
automeister exec screen.capture --output /tmp/after.png --json
# Agent confirms UI changed as expected
```

### Using JSON Output Mode

Always use `--json` for agent interaction:

```bash
automeister --json exec screen.find button.png
```

Output:
```json
{
  "success": true,
  "result": {
    "x": 450,
    "y": 320,
    "width": 100,
    "height": 40,
    "confidence": 0.95,
    "center_x": 500,
    "center_y": 340
  }
}
```

Error output:
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

### Error Handling Patterns

Always check exit codes and parse JSON responses:

```bash
# Check if operation succeeded
result=$(automeister --json exec screen.find button.png)
if echo "$result" | jq -e '.success' > /dev/null; then
    x=$(echo "$result" | jq '.result.center_x')
    y=$(echo "$result" | jq '.result.center_y')
    automeister exec mouse.click-at "$x" "$y"
fi
```

---

## Screen Analysis Strategies

### When to Use Screenshot + Multimodal Vision

**Best for:**
- Understanding complex UI layouts
- Reading dynamic content
- Identifying elements that change appearance
- Analyzing visual relationships between elements

**Example scenario:** "Find the red error message and read what it says"

```bash
automeister exec screen.capture --output /tmp/screen.png
# Agent analyzes image with multimodal vision
# Agent identifies error location and content visually
```

### When to Use OCR

**Best for:**
- Extracting specific text content
- Verifying text appeared/changed
- Reading forms, labels, status messages
- When you know what text to expect

**Example scenario:** "Wait for 'Login successful' message"

```bash
automeister exec screen.wait-for-text "Login successful" --timeout 10
```

**Example scenario:** "Read the current value in the price field"

```bash
automeister --json exec screen.ocr --region 200,150,100,30
# Returns: {"text": "$49.99", "region": [200, 150, 100, 30]}
```

### When to Use Template Matching

**Best for:**
- Finding consistent UI elements (icons, buttons)
- Locating elements with known visual appearance
- Click targets that don't change
- Faster than full vision analysis

**Example scenario:** "Click the save icon"

```bash
result=$(automeister --json exec screen.find save-icon.png --threshold 0.85)
if [ $? -eq 0 ]; then
    x=$(echo "$result" | jq '.result.center_x')
    y=$(echo "$result" | jq '.result.center_y')
    automeister exec mouse.click-at "$x" "$y"
fi
```

### Combining Approaches

Often the best strategy combines multiple approaches:

```
1. Use template matching to find a known region (e.g., dialog box)
2. Use OCR on that region to read content
3. Use multimodal vision for complex decisions
4. Use template matching to click buttons
```

**Example: Handling a Confirmation Dialog**

```bash
# 1. Wait for dialog to appear (template match)
automeister exec screen.wait-for-image dialog-header.png --timeout 5

# 2. Read the dialog message (OCR)
message=$(automeister --json exec screen.ocr --region 100,200,400,100 | jq -r '.result.text')

# 3. Agent decides based on message content

# 4. Click appropriate button (template match)
automeister exec mouse.click-image ok-button.png
```

---

## Reliable Interaction Patterns

### Always Verify Before Clicking

Never click based on assumed coordinates. Always verify the target exists:

```bash
# BAD: Assuming button is at fixed position
automeister exec mouse.click-at 500 300

# GOOD: Find button first, then click
result=$(automeister --json exec screen.find submit-button.png)
if echo "$result" | jq -e '.success' > /dev/null; then
    automeister exec mouse.click-image submit-button.png
else
    echo "Button not found - UI may have changed"
fi
```

### Use Wait-For Before Interacting

UI elements may take time to appear. Always wait:

```bash
# Wait for element to appear before clicking
automeister exec screen.wait-for-image loading-complete.png --timeout 30
automeister exec mouse.click-image next-button.png
```

```bash
# Wait for text confirmation before proceeding
automeister exec screen.wait-for-text "Ready" --timeout 10
automeister exec keyboard.type "next command"
```

### Implement Retry Logic

Network delays, animations, and timing can cause failures. Implement retries:

```bash
max_attempts=3
attempt=1

while [ $attempt -le $max_attempts ]; do
    if automeister --json exec screen.find target.png > /dev/null 2>&1; then
        automeister exec mouse.click-image target.png
        break
    fi
    echo "Attempt $attempt failed, retrying..."
    sleep 1
    attempt=$((attempt + 1))
done
```

### Handle Timing Issues

Add appropriate delays for:
- Page loads
- Animations
- Network requests
- UI transitions

```bash
# After clicking a menu, wait for it to expand
automeister exec mouse.click-image menu-button.png
automeister exec delay 0.3
automeister exec mouse.click-image menu-item.png

# After form submission, wait for response
automeister exec keyboard.key Return
automeister exec screen.wait-for-text "Saved" --timeout 10
```

---

## Common Workflows

### Opening Applications

```bash
# Method 1: Application menu
automeister exec keyboard.hotkey "super"
automeister exec delay 0.5
automeister exec keyboard.type "firefox"
automeister exec delay 0.3
automeister exec keyboard.key Return

# Method 2: Direct command
automeister exec shell "firefox &"

# Wait for window to appear
automeister exec window.wait-for "Firefox" --timeout 10
```

### Form Filling

```bash
# Focus the form field first
automeister exec mouse.click-image username-field.png
automeister exec delay 0.1

# Clear existing content
automeister exec keyboard.hotkey "ctrl+a"
automeister exec keyboard.type "newusername"

# Tab to next field
automeister exec keyboard.key Tab
automeister exec keyboard.type "password123"

# Submit
automeister exec keyboard.key Return
```

### Menu Navigation

```bash
# Open menu
automeister exec mouse.click-image file-menu.png
automeister exec delay 0.2

# Navigate with keyboard
automeister exec keyboard.key Down
automeister exec keyboard.key Down
automeister exec keyboard.key Return

# Or click directly
automeister exec mouse.click-image save-option.png
```

### Dialog Handling

```bash
# Wait for dialog
automeister exec screen.wait-for-image dialog-box.png --timeout 5

# Read dialog content with OCR
automeister --json exec screen.ocr --region 100,150,300,100

# Handle based on content
automeister exec mouse.click-image ok-button.png

# Verify dialog closed
automeister exec delay 0.3
if ! automeister --json exec screen.find dialog-box.png --threshold 0.9 > /dev/null 2>&1; then
    echo "Dialog closed successfully"
fi
```

### Multi-Window Workflows

```bash
# List available windows
automeister --json exec window.list

# Focus specific window
automeister exec window.focus "Document.pdf"

# Arrange windows side by side
automeister exec window.move "Terminal" 0 0
automeister exec window.resize "Terminal" 960 1080
automeister exec window.move "Browser" 960 0
automeister exec window.resize "Browser" 960 1080
```

---

## Troubleshooting

### Element Not Found

**Symptoms:** `screen.find` returns no match, `ImageNotFoundError`

**Causes & Solutions:**

1. **Threshold too high**
   ```bash
   # Lower the threshold
   automeister exec screen.find button.png --threshold 0.7
   ```

2. **UI appearance changed**
   - Capture a new template image
   - Use grayscale matching for color variations
   ```bash
   automeister exec screen.find button.png --grayscale
   ```

3. **Element not on screen**
   - Scroll the view
   - Switch to correct window/tab

4. **Element loading**
   - Use `wait-for` with timeout
   ```bash
   automeister exec screen.wait-for-image button.png --timeout 10
   ```

### Timing Issues

**Symptoms:** Actions happen too fast, clicks miss targets

**Solutions:**

1. **Add delays between actions**
   ```bash
   automeister exec mouse.click-image menu.png
   automeister exec delay 0.3
   automeister exec mouse.click-image item.png
   ```

2. **Use wait-for instead of fixed delays**
   ```bash
   automeister exec screen.wait-for-text "Ready"
   ```

3. **Verify state before acting**
   ```bash
   while ! automeister --json exec screen.find target.png > /dev/null 2>&1; do
       sleep 0.5
   done
   ```

### Coordinate Drift

**Symptoms:** Clicks land in wrong places, especially after screen changes

**Causes & Solutions:**

1. **Window moved/resized**
   - Use `window.focus` before interacting
   - Use relative template matching, not absolute coordinates

2. **Display scaling changed**
   - Recapture template images at current scale

3. **Multi-monitor issues**
   - Specify which display in config
   - Use window-relative coordinates

### OCR Accuracy

**Symptoms:** Text not recognized, wrong characters

**Solutions:**

1. **Use appropriate region**
   ```bash
   # Narrow down to just the text area
   automeister exec screen.ocr --region 200,150,100,30
   ```

2. **Check language setting**
   ```bash
   automeister exec screen.ocr --lang eng+fra
   ```

3. **Preprocess the image**
   - Capture at higher resolution
   - Ensure good contrast

4. **Use substring matching**
   ```bash
   # Don't require exact match
   automeister exec screen.wait-for-text "Success"  # matches "Success!" too
   ```

---

## MCP Integration Guide

See [MCP.md](MCP.md) for detailed MCP server setup and tool documentation.

### Quick Setup

1. Install Automeister with MCP support
2. Add to `.mcp.json`:
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
3. Claude Code now has access to all Automeister tools

### Example MCP Tool Calls

**Screen capture for analysis:**
```
tool: screen_capture
args: {}
```

**Click at coordinates:**
```
tool: mouse_click
args: {x: 500, y: 300, button: "left"}
```

**Type text:**
```
tool: keyboard_type
args: {text: "Hello, World!"}
```

**Focus window:**
```
tool: window_focus
args: {title: "Firefox"}
```

---

## Best Practices Summary

1. **Always use `--json`** for machine-readable output
2. **Verify before acting** - find elements before clicking
3. **Wait for state changes** - use `wait-for` commands
4. **Implement retries** - handle transient failures
5. **Combine approaches** - template matching + OCR + vision
6. **Handle errors gracefully** - check exit codes and error responses
7. **Add appropriate delays** - UI needs time to respond
8. **Use window management** - focus correct window before interaction
9. **Keep templates updated** - recapture when UI changes
10. **Log actions** - record what's happening for debugging
