# Pakk Package Manager

**Simple package manager using GitHub / GitLab / etc. as package index.**

Originally designed for supporting the development on robotics applications using ROS 2, pakk is a flexible pakkage manager using GitHub as pakkage index.
Pakk not only supports the installation of pakkages of different types, but also (auto-)starting / stopping of executable pakkages.

> [!NOTE]
> Pakk is still in early development and might not be stable yet. Please report any issues you encounter.


**TL;DR:**
```bash
# Install
pip install pakk-package-manager
# Setup
pakk setup

# Install a pakkage
pakk install <PAKKAGE_NAME>
# Start the pakkage
pakk start <PAKKAGE_NAME>
```

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
  - **Static Web** pakkages (built webapps) (work in progress)
  - **Dynamic Web** pakkages (reverse proxy apps) (work in progress)

### Management of Pakkages:
- starting / stopping of executable pakkages
- enabling / disabling of executable pakkages for autostart
- automatic update of installed pakkages

<!-- Future Work:
- installation of multiple versions of a pakkage -->


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

> [!NOTE]
> The process of creating a pakkage can be supported by using the `pakk init` command, which interactively creates a `pakk.cfg` file in the current directory.
> However, for a more detailed creation, you might want to manually create/adapt the `pakk.cfg` file.

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

|Directory     |Content                                            |
|--------------|---------------------------------------------------|
|[`docs`](docs)|Pakk usage and developer documentation.            |
|[`pakk`](pakk)|The python package containing the pakk source code.|
<!-- MD+FIN:generate.content -->

# Documentation

A more detailed documentation can be found at [`docs/README.md`](docs/README.md).

> [!NOTE]
> The documentation is still in progress and might not be complete yet. If you have any questions or suggestions, feel free to open an issue or a discussion.

# Questions & Issues

If you encounter any problems, please [open an issue](https://github.com/icampus-wildau/pakk/issues).
If you have any questions, feel free to ask them in the [Discussions](https://github.com/icampus-wildau/pakk/discussions) section.

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
