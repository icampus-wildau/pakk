<!-- MD+:META
title = "Creating Packages"
 -->

# Creating a pakkage

To create your own pakkage, you need to specify a `pakk.cfg` file in the root of your repository.
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
