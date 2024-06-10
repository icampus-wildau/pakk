<!-- MD+:META
title = "Developing new Connectors"
 -->

# What are Connectors

Connector are on of the basic elements of pakk, allowing the connection to a pakkage-index.
This connection allows the discovery and the fetching from the index in order to install a pakkage.
By default, pakk includes connectors for GitHub and GitLab.

If you have your repositories / projects stored somewhere else and want to use pakk to access these projects, you can easily develop your own connector.

# Develop a custom connector

To create a connector, define a class inheriting from the `pakk.modules.connector.Connector` base class.

In your class, you have to:
- override the discover() method
- override the fetch() method

Furthermore, you can:
- override the priority of the connector
- define the configuration of the connector

## Discovering process



## Fetching process



## Where to place connectors

Place your connector implementations either at:
- `pakk_your_package.connector.*` or
- `pakk_your_package.modules.connector.*`

All files in this directories are automatically loaded and scanned for classes inheriting from `Connector`.

Example:
```txt
pakk_your_custom_connector
|- __init__.py
|-  connector
    |- __init__.py
    |- my_connector.py
```

In `my_connector` you can define and implement the connector class (or multiple classes) inheriting from `Connector`.

## What if the connector is located in a subpackage

If your connector contains multiple files located in a subdirectory, import your Connector class and define the `__all__` property in the `__init__.py` of your connector package.

Given the following package structure of your connector package:
```txt
pakk_your_custom_connector
|-  __init__.py
|-  connector
    |-  __init__.py
    |-  my_complex_connector
        |-  __init__.py (<-- this is important!)
        |- my_connector_implementation.py
        |- some_other_files.py
```

... put something like this in the inner `__init__.py`:
```python
from pakk_your_custom_connector.connector.my_complex_connector.my_connector_implementation import MyConnector

# Add this to allow automatic connector loading
__all__ = ["MyConnector"]
```


# How to Configure Connectors

# How to Run Setups for the Connector

# Priority of a connector

# Caching of projects
