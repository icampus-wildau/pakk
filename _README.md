#MD+:include("./docs/AUTHORS.md")

---

# **Pakk** Package Manager

The Package Manager for ROS-E.

# Table of Contents

[[_TOC_]]

# #MD+:snippet.installation("./")

# Pakk Quickstart

The following will summarize the most important commands and their options for the usage of pakk.
For full documentation enter `pakk -h` or `pakk [CMD] -h` for a specific command.

# Setup pakk for your system

After the first installation you want to setup pakk properly.

```
# Run the configuration setup for Pakk. This helps you to interactively create a pakk.cfg configuration file.
pakk config

# Run the setup for Pakk. This initiates all necessary rights and files to let Pakk run successfully. Run this AFTER you have created a pakk.cfg file.
pakk setup
```

## Install Pakkages

```bash
pakk install PAKKAGE
```

Install a PAKKAGE (or multiple PAKKAGES).
You can specify a version with PAKKAGE@VERSION.
 If no version is specified, the latest version will be installed.

Options:
- `-F`, --force-reinstall: Reinstall defined pakkage even if it is already installed and up-to-date.
- `--refetch`: Refetches the pakkage from the server, otherwise already fetched pakkages are reused. Use in combination with `--force-reinstall` to reinstall a clean fetched copy of the package.
- `-U`, --upgrade: Upgrade all specified packages to the newest available version.
- `--clear-cache`: Clear the complete cache before installing. Use if you don't find versions that should be actually available.
- `--dry-run`: Don't actually install anything, just print what would be.
- `--no-deps`: Don't install pakkage dependencies.


## List

```bash
pakk ls -a ros2 # List all available ros2 pakkages, also non installed ones
```

List all installed pakkages. You can optionally specify a REGEX_FILTER expression to filter the list.

Options:
- -a, --all: Show all available pakkages.
- -x, --extended: Show extended information.
- -t, --types: Show the install types of the pakkage.

## Execution of Pakkages

### Run
```bash
pakk run PAKKAGE
```
Runs the given pakkage interactively.

### Start
```bash
pakk start PAKKAGE
```
Starts the given pakkages as services.

### Enable
```bash
pakk enable PAKKAGE
```
Enables the given pakkages.

### Stop
```bash
pakk stop PAKKAGE
```

Stops the given pakkage services.

### Disable
```bash
pakk disable PAKKAGE
```

Disables the given pakkages.


### Restart
```bash
pakk restart PAKKAGE
```

Restarts the given pakkages.

Options:
- `-r`, `--running`: Only restart running pakkages.
- `-e`, `--enabled`: Only restart enabled pakkages.

### Log
```bash
pakk log PAKKAGE
```
Follows the log of the given executable pakkage.

### Status

```bash
pakk status
```

Shows the status of startable pakkages in the system.


### Source

```bash
$(pakk source)
```

Sources the environment with all settings from the installed pakkages.
Installed pakkages can come with environment variables, which are sourced with this command to be used in manual testing.
These environment variables are necessary for the correct execution of other pakkages.

Just execute `pakk source` to see the environment variables that are set by pakk. `$()` is used to execute the output in the current shell.


## Other commands

### Tree
```bash
pakk tree
```

Show the dependency tree of a pakkage.

Options:
- -d, --depth: Maximum depth of the tree. 0 prints the complete tree.


### Init

```bash
pakk init PATH
```

Initialize a pakkage in the given path.

### Ros2
Run a ROS node from a package. Just type `pakk ros2` to see all available packages and nodes with auto completion.

```
$ pakk ros2
> ros2 run respeaker reSpeaker
```


# Creating a pakkage

To create your own pakkage, you need to specify a `pakk.cfg` file in the root of your pakkage.
You can use the `pakk init` command to interactively initialize a new pakkage in the current directory and create a `pakk.cfg` file, that can be edited afterwards.

The `pakk.cfg` file contains all necessary information about your pakkage:
- the unique `id` of your pakkage
- the `title` of your pakkage
- the current `version` of your pakkage
- the `description` of your pakkage
- the `keywords` of your pakkage
- the `dependencies` of your pakkage
- the `pakkage types` defining the installation process of your pakkage

## Basic information of your pakkage

The following information are always necessary for your pakkage:

```ini
[info]
id = your-pakkage-id
version = 1.2.3
title = Your Pakkage Title
description = Short description of your pakkage
keywords = some, keywords, for, your, pakkage

[dependencies]
other-package-id-1 = ^1.0.0
other-package-id-2 = ^0.3.0
other-package-id-3 = ^2.0.0
```

## Basic Pakkage types

To define the installation process of your pakkage, you can define one or multiple pakkage types. Pakkage types can be arbitrarily combined.

There are a few predefined pakkage types:
- `Setup`: Installs a pakkage with prepended setup instructions.
- `Python`: Installs a pakkage as python package.
- `ROS2`: Installs a pakkage as ros2 package.
- `Asset`: Installs a pakkage as asset, e.g. for data-files, pretrained models, etc.

### Setup
Most packages will need a setup process, that is executed before the actual installation of the pakkage.

In the setup you can define:
- `apt`: A list of apt packages to install.
- `pip`: A list of pip packages to install (or the requirements.txt file).
- `script`: A custom script to execute before the installation.

```ini
[Setup]
apt = apt-package-1 apt-package-2
pip = requirements.txt # Or pip-package-1 pip-package-2
script = ./setup_script.sh
```

### Python

This pakkage type just installs the pakkage as python package without further configuration.

```ini
[Python]
```

### ROS2

This pakkage type installs the pakkage as ros2 package. Besides the installation you can define a launch script as entry point for this pakkage, to make it startable with `pakk start`.

```ini
[ROS2]
start = ros_package_name the_launch_script.launch.py
# Define if the pakkage should be started with ROS_LOCALHOST_ONLY=1, to only allow communication with local nodes.
# Defaults to true, so you only need to set it to false if you want communication with nodes on other machines.
local = False
```

### Asset

This pakkage type installs the pakkage as asset. Assets can be e.g. used for:
- data files
- pretrained models
- environment variables
- thus, everything that is needed for the execution of other pakkages

#### Environment variables

The best practice for Asset-pakkages that include data files is the creation of environment variables, that can be used in other pakkages.

```ini
[Asset]
# In this case we create an environment variable that points to the data file found in the data directory of this asset pakkage.
# Other pakkages can use this environment variable CUSTOM_DATA_FILE to access the data file.
CUSTOM_DATA_FILE=./data/custom_data_file.dat
```

This environment variable is automatically passed to the environment of other pakkages, as soon as they are executed (with `pakk start` or `pakk run`).
In this way you can avoid the definition of absolute paths in your pakkages and make them more portable.

#### Softlinks

You can create softlinks in your pakkage with the `link` option. This is for example useful for aliasing files.

```ini
[Asset]
link = ./extremely_long_model_name.onnx ./short_alias.onnx
       ./extremely_long_model_name.onnx.json ./short_alias.onnx.json
       # Go on with more pairs of files to link
```

We do not recommend the usage of softlinks for locations outside your pakkage directory, but in case you need to, you can do this with the following syntax:

```ini
[Setup]
# We can define **local** variables for the installation process of the pakkage in the setup section.
$MODEL = my-model-name

[Asset]
# Global wnvironment variable for other pakkages.
MY_MODEL_NAME = $MODEL
# Link the model to the target directory /opt/pakk/my_models
linke = ./$MY_MODEL_NAME /opt/pakk/my_models/$MY_MODEL_NAME
# If there is an environment variable that defines the target directory, we can use it as well. The following syntax searches for TARGET_DIR if exists, otherwise it uses the default value.
link = ./$MY_MODEL_NAME ${TARGET_DIR:-/opt/pakk/my_models}/$MY_MODEL_NAME
```

Only use directories you have access to. For pakk there is a special directory `/opt/pakk` that is created during the setup process and is accessible for all pakkages.

---
