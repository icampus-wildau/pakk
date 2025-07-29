# Run Options Feature

This feature allows you to pass CLI arguments to the `pakk run`, `pakk start`, and `pakk enable` commands that will be converted to environment variables for the running pakkage.

## Overview

The run options feature supports three different approaches for defining CLI arguments to environment variable mappings:

### Approach 1: Simple Assignment in pakk.cfg

Define simple mappings in the `[RunOptions]` section of your `pakk.cfg` file:

```ini
[RunOptions]
-d = MICROPHONE_DEVICE_NAME
--device = MICROPHONE_DEVICE_NAME
--port = SERIAL_PORT
--baud = BAUD_RATE
```

**Usage:**
```bash
pakk run respeaker -d=mydevice
pakk start respeaker --port=/dev/ttyUSB0
pakk enable respeaker --baud=115200
```

### Approach 2: Dynamic Options with Type and Help

Define more complex options with type information and help text:

```ini
[RunOptions]
device = {type: str, env: MICROPHONE_DEVICE_NAME, help: "Microphone device name", default: "default_device"}
port = {type: int, env: SERIAL_PORT, help: "Serial port number", default: 9600}
config = {type: str, env: CONFIG_FILE_PATH, help: "Configuration file path"}
```

**Usage:**
```bash
pakk run respeaker device=mydevice
pakk start respeaker port=115200
pakk enable respeaker config=/path/to/config.yaml
```

### Approach 3: Arbitrary Environment Variables

Use the `--env-` prefix to set any environment variable directly:

```bash
pakk run respeaker --env-MICROPHONE_DEVICE_NAME=mydevice --env-SERIAL_PORT=/dev/ttyUSB0
pakk start respeaker --env-DEBUG_MODE=true --env-LOG_LEVEL=debug
pakk enable respeaker --env-CUSTOM_VAR=value
```

## Supported Commands

The run options feature works with the following commands:

- `pakk run` - Run a pakkage interactively
- `pakk start` - Start a pakkage as a service
- `pakk enable` - Enable a pakkage for autostart

## Service Integration

When using `pakk start` or `pakk enable`, the run arguments are included in the generated systemd service file. This means the environment variables will be available every time the service starts.

## Environment Variable Processing

The run arguments are processed in the following order:

1. **Simple mappings** from the `[RunOptions]` section
2. **Dynamic options** from the `[RunOptions]` section  
3. **Arbitrary environment variables** with the `--env-` prefix

The environment variables are set using the existing `Process.update_temp_env_vars()` system, which makes them available to the running pakkage.

## Example pakk.cfg

Here's a complete example of a `pakk.cfg` file with run options:

```ini
[info]
id = test/respeaker
version = 1.0.0
title = Test Respeaker Package
description = A test package to demonstrate run options functionality
keywords = test, respeaker, microphone

[dependencies]

[Setup]
apt = python3-pip

[RunOptions]
# Simple assignments
-d = MICROPHONE_DEVICE_NAME
--device = MICROPHONE_DEVICE_NAME
--port = SERIAL_PORT
--baud = BAUD_RATE

# Dynamic options
device = {type: str, env: MICROPHONE_DEVICE_NAME, help: "Microphone device name", default: "default_device"}
port = {type: int, env: SERIAL_PORT, help: "Serial port number", default: 9600}
config = {type: str, env: CONFIG_FILE_PATH, help: "Configuration file path"}

# Direct environment variables
--env-DEBUG_MODE = DEBUG_MODE
--env-LOG_LEVEL = LOG_LEVEL

[ROS2]
start = ros2 launch respeaker_ros2 respeaker.launch.py
```

## Usage Examples

```bash
# Simple assignment
pakk run respeaker -d=mydevice

# Dynamic options
pakk run respeaker device=mydevice port=115200

# Arbitrary environment variables
pakk run respeaker --env-MICROPHONE_DEVICE_NAME=mydevice --env-SERIAL_PORT=/dev/ttyUSB0

# Start as service with arguments
pakk start respeaker -d=mydevice --env-DEBUG_MODE=true

# Enable with arguments
pakk enable respeaker device=mydevice port=115200
```

## Implementation Details

The feature is implemented using:

1. **RunOptionsInstructionParser** - Parses the `[RunOptions]` section in `pakk.cfg`
2. **TypeRunOptions** - A pakkage type that can be combined with other types to add CLI argument support
3. **parse_run_arguments()** - Helper function that converts CLI arguments to environment variables
4. **Updated CLI commands** - Modified `run`, `start`, and `enable` commands to accept additional arguments
5. **Updated service generation** - Modified `PakkChildService` to include run arguments in systemd service files

## Backward Compatibility

This feature is fully backward compatible. Existing pakkages without `[RunOptions]` sections will continue to work exactly as before. The new functionality is only activated when run arguments are provided or when a `[RunOptions]` section is present in the pakkage configuration. 