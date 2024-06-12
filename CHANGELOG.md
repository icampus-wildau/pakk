# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Future work

Supported Pakkage Types:
- Setup
- Python
- Asset
- Static web apps
- Dynamic web apps

Commands:
- ros2
- log
- source

Logging:
- add installation logging
- add runtime logging

Configuration:
- allow per-pakkage configuration settings


Plugins:
- support for dynamic integration of new commands and new options for existing commands

## [UNRELEASED]

## [0.4.0]

Fixes and changes:
- General:
  - restructured project directories and names (thus, some import names has been changed)
- Actions:
  - [Update] Is now waiting to have an internet connection to work properly on system start
  - [Update] Now uses the correct pip command to update pakk
- Types:
  - [ROS] Fixed execution of ROS packages by adapting the PYTHONPATH according to the venv
  - [Setup] Fixed installation instruction parsing
  - [Setup] Now checks for failed commands
- Setup routines: 
  - dir creation in first run of group setup routine


## [0.3.0]

Working commands
- install
- list
- update
- configure
- manager:
  - status
  - run
  - start
  - stop
  - enable
  - disable
  - restart
- setup
- configure
- init
- tree

Working pakkage types:
- ROS2
- Setup, Asset and Python should work, but not tested yet

Basic documentation.
