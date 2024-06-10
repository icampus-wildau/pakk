from __future__ import annotations

import json

from pakk.pakkage.core import PakkageConfig

json_str = """{
    "id": "ros2-basic-user-actions",
    "version": "0.1.5",

    "info": {
        "title": "ROS2 Basic User Actions",
        "description": "Basic User Actions / Interactions offered by ROS-E.",
        "keywords": [
            "ros2",
            "commands",
            "interactions"
        ]
    },

    "dependencies": [
        {
            "id": "ros2-flint",
            "version": ">=0.2.0"
        },
        {
            "id": "ros2-displays",
            "version": "^1.0.0"
        },
        {
            "id": "ros2-resource-manager",
            "version": "^0.3.0"
        }
    ],

    "ros": {
        "type": "library",
        "package": "basic_user_actions"
    }
}

"""

cfg = PakkageConfig.from_json(json.loads(json_str))
d = cfg.cfg.__dict__
x = 5

cfg.cfg.write(open("__temp.cfg", "w"))
