# Pakk Package Manager

**Simple package manager using GitHub / GitLab / etc. as package index.**

Originally designed for supporting the development on robotics applications using ROS 2, pakk is a flexible pakkage manager using GitHub as pakkage index.
Pakk not only supports the installation of pakkages of different types, but also (auto-)starting / stopping of executable pakkages.

# Features & Compatibility

> [!NOTE]
> At the moment, pakk is designed and tested to work on **Linux/Ubuntu**. However, some features might work out of the box on any OS (without guarantees) and the library is designed to be easily extensible in future.

### Installation of Pakkages:
- discovery of pakkages hosted on GitHub (or other sources using add-ins)
- dependency resolving
- installation of different **pakkage types**. Out-of-the-box available types:
  - **ROS 2** (Robot Operating System 2) pakkages
  - **Python** pakkages
  - **Asset** pakkages (static data like images, audio, neural networks, etc.)
  - **Static Web** pakkages (built webapps) (WIP)
  - **Dynamic Web** pakkages (reverse proxy apps) (WIP)

### Management of Pakkages:
- starting / stopping of executable pakkages
- enabling / disabling of executable pakkages for autostart
- automatic update of installed pakkages

<!-- Future Work:
- installation of multiple versions of a pakkage -->


> [!IMPORTANT]
> Any 'Getting Started' sections should follow now. By default, this template includes a 'Getting Started' section that uses the [pakk](https://github.com/icampus-wildau/pakk) package manager and a manual installation section. If this software cannot be installed using `pakk`, remove the 'Getting Started with pakk' section. If there are other ways to install the software, add them here. Always having a 'Getting Started from Scratch' section is generally recommended. If the software is not meant to be installed, but rather used as a library or a service, make sure to include the necessary information on how to use it.

<!-- MD+:generate.getting_started.pakk -->
# Getting Started with [pakk](https://github.com/icampus-wildau/pakk)
<!-- MD+FIN:generate.getting_started.pakk -->

See the [Examples](#examples) section for more information on how to use this project.

# Getting Started

## Installation of `pakk`

```bash
# Install pakk from pip
pip install pakk-package-manager
# or from source
pip install git+https://github.com/icampus-wildau/pakk
```

> [!NOTE]
> Make sure, that your path for installed python packages is added to PATH in order to make pakk executable.
> If `pakk`is not found as command, add something like `export PATH="$PATH:/home/user/.local/bin"` to your `~/.bashrc`.

## Setup and Configuration of `pakk`

After the installation, you need to setup pakk for your system.
This includes the creation of the necessary directories and files.
Some features of pakk require root access, so you might need to enter your password during the setup process.

> [!IMPORTANT]
> Do **NOT** run the setup as root with `sudo pakk setup`, just call `pakk setup` and enter your authentication when asked.

```bash
pakk setup
```
---

By default, pakk uses its standard configuration, including default paths for the installed packages, etc.
To adapt these configurations, you can run:
- `pakk cfg main` for the main settings
- `pakk cfg <connector_name>` for connector settings (e.g. `pakk cfg GithubConnector` to configure the connection to GitHub)

You can easily skip this step and continue with the default settings.

## Install and start a pakkage

```bash
pakk install PACKAGE_NAME
# e.g. pakk install icampus-wildau/ros-i2c
```

When installing a pakkage, all required setup setups are executed and all dependencies are installed as well.

After installation, you can list your installed pakkages:
```bash
pakk ls
```

If the installed pakkage is executable, you can start it with:
```bash
# Run it interactively
pakk run PACKAGE_NAME

# Start it as a service
pakk start PACKAGE_NAME
# Enable it for autostart
pakk enable PACKAGE_NAME

# Stop it
pakk stop PACKAGE_NAME
# Disable it for autostart
pakk disable PACKAGE_NAME

# See the status of all startable pakkages
pakk status
```

You can enter `pakk -h` or `pakk [CMD] -h` to get an overview of other available commands and options for specific commands.

## Create a pakkage

You can transform every of your projects/repositories to a *pakkage* by:
- adding a `pakk.cfg` with your pakkage specifications to your project
- releasing the pakkage on your index, e.g. if using GitHub by adding a tag

The `pakk.cfg` contains meta-information about your pakkage with at least the following:
```ini
# The obligatory meta-information
[info]
# The unique id of your pakkage matching the GitHub url suffix.
id = my_name/my_pakkage
# The current version (using semantic versioning) of your pakkage.
# This should match the tag of the release.
version = 1.2.5
# A short title
title = My Pakkage - a beautiful pakkage example
# A short description what your pakkage is for
description = Base framework for Flexible Intent Recognition
# Optionally a list of keywords
keywords = keyword1, keyword2

# Optionally the dependencies
[dependencies]
my_name/my_other_pakkage = ^0.5.0
some_org/another_pakkage = ^1.4.0

# Definition of the pakkage type
```

After the obligatory definition of the pakkage and the dependencies, one or multiple pakkage types can be added, to define the installation process. 
See [the docs for creating a pakkage](./docs/creating_packages.md) for a list of out-of-the-box supported types. 



See the [Examples](#examples) section for more information on how to use this project.

# Usage Examples

> [!IMPORTANT]
> Add some basic examples on how to use the package here. These examples should be easy to understand and should cover the most important use cases. Always include the necessary imports and the expected output, but assume that the user has already gone through a 'Getting Started' section.

For more examples and advanced topics, please refer to the [Documentation](docs/README.md) or have a look at the [Examples](examples/README.md) directory.

<!-- MD+:generate.content
header = '# Contents of this Repository'
level = 1
dirs = True
md_files = False
-->
# Contents of this Repository

|Directory             |Content                                                     |
|----------------------|------------------------------------------------------------|
|[`docs`](docs)        |The documentation for the {{ Name of the Project }} project.|
|[`examples`](examples)|Examples for the {{ Name of the Project }} project.         |
<!-- MD+FIN:generate.content -->

> [!IMPORTANT]
> This section should contain a list of important files and directories in the repository. By default, this section is auto-generated by Markdown Plus.

# Documentation

> [!IMPORTANT]
> Point users to an in-depth documentation of the software here. The documentation should focus on more advanced topics and detailed interface descriptions. Including examples and tutorials is a good idea. There is usually no good reason to remove this section.

A more detailed documentation can be found at [`docs/README.md`](docs/README.md).

# Questions & Issues

If you encounter any problems, please [open an issue](https://github.com/icampus-wildau/pakk/issues). If you have any questions, feel free to ask them in the [Discussions](https://github.com/icampus-wildau/pakk/discussions) section.

# Contributing

**Any contributions to extend the functionality or to solve existing problems are welcome!**

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file before contributing to this project and follow the guidelines provided there. Also, make sure to read and follow the [Code of Conduct](https://github.com/icampus-wildau/.github/blob/main/.github/CODE_OF_CONDUCT.md).

# Development setup

```bash
git clone https://github.com/icampus-wildau/pakk
cd pakk
git checkout dev
pip install -e .
```

# FAQ

## You know, that "package" is spelled with "ck" and not with "kk"?!?

Yeah, we know :-)


# License

This project is licensed under the Apache License 2.0. For details, please see the [LICENSE](LICENCE) file. By contributing to this project, you agree to abide by the terms and conditions of the Apache License 2.0.






**TEAM** <br>
[Valentin Schröter](mailto:vasc9380@th-wildau.de) <br>

---

# **Pakk** Package Manager

The Package Manager for ROS-E.

# Table of Contents

[[_TOC_]]

# Installation

## Standalone from Git

```bash
# Clone repo from origin
git clone https://icampusnet.th-wildau.de/ros-e/software/infrastructure/pakk-package-manager.git

# If this should be a standalone python package, install it in your system
cd pakk-package-manager
# Normale installation
pip install .
# Editable installation, choose this if you want to edit the code for further development
pip install -e .
```

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

### Static Web

This pakkage type installs the pakkage as static web package. This means, that the static built distribution files of your project are served by a nginx webserver under a specific path.

The configuration allows you to specify, whether the app should be installed and built before being served or not.

```ini
[Web]
# The root directory of the static files to serve.
static_root = ./my_app/dist/

# The path under which the static files are served.
# If not given, it defaults to the id of the pakkage.
# In this case your app is served under http://ip.to.your.server/static_web_dummy/
public_path = /static_web_dummy/

# Optional parameter to specify the build system, one of [yarn, npm].
# If given, your project is installed and build before being served.
# For the build, the environment variables BASE, BASE_URL and PUBLIC_PATH are set to `public_path`.
# If your app requires a different environment variable or even a build option for the public path, see the next options to specify them.
# If your project already includes the distribution files, you can omit this parameter.
build = yarn
# The directory of your project as root for the install and build process.
# Can be omitted if build is omitted.
build_dir = ./my_app/

# Optional parameter to specify the environment variable for the public path used in the build process.
public_path_env_var = SOME_PUBLIC_PATH

# Optional parameter to specify the build option for the public path used in the build process.
# E.g. quasar does not support the environment variable PUBLIC_PATH, but the build option --base.
public_path_build_option = --base

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


 Generated with [Markdown Plus](https://icampusnet.th-wildau.de/ros-e/software/infrastructure/markdown-plus)
