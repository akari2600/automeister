# Automeister

A desktop-agnostic GUI automation framework for Debian Linux, designed for AI agent integration.

## Overview

Automeister provides Keyboard Maestro-style automation capabilities on Linux without dependency on any specific desktop environment's accessibility APIs. It operates at the X11/display server level, using screen capture, image recognition, and input simulation to interact with any GUI application.

## Features

- **Desktop Agnostic**: Works on XFCE, GNOME, KDE, or any X11-based environment
- **CLI-First**: All operations accessible via command line for easy agent integration
- **Composable**: Small, focused primitives that combine into complex workflows
- **Parameterized**: Macros accept runtime parameters for dynamic behavior
- **Inspectable**: Clear logging and debugging output for troubleshooting

## Quick Start

### Prerequisites

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt install xdotool scrot maim imagemagick tesseract-ocr wmctrl xwininfo xprop

# Install Automeister
pip install automeister
```

### Basic Usage

```bash
# Take a screenshot
automeister exec screen.capture --output screenshot.png

# Click at coordinates
automeister exec mouse.click-at 500 300

# Type text
automeister exec keyboard.type "Hello, World!"

# Find and click an image on screen
automeister exec mouse.click-image button.png

# Run a macro
automeister run my-workflow --param username=test
```

## Documentation

- [Specification](docs/SPEC.md) - Complete technical specification
- [CLI Reference](docs/CLI.md) - Command-line interface documentation
- [Architecture](docs/ARCHITECTURE.md) - System design and architecture
- [Macro Guide](docs/MACROS.md) - Writing and managing macros

## Project Status

This project is in active development. See the [Linear project](https://linear.app/vyomanautika/project/automeister-69f64a0fc042) for current progress.

### Implementation Phases

1. **Phase 1: Core Foundation** - Project structure, CLI, basic input/screen control
2. **Phase 2: Image Recognition** - OpenCV template matching
3. **Phase 3: Macro System** - YAML macros, parameters, variables
4. **Phase 4: Flow Control** - Conditionals, loops, error handling
5. **Phase 5: Advanced Features** - OCR, window management, debugging
6. **Phase 6: Polish** - Error messages, optimization, documentation, tests

## License

MIT License - see [LICENSE](LICENSE) for details.
