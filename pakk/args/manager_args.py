from __future__ import annotations

from pakk.args.base_args import BaseArgs


class ManagerArgs(BaseArgs):
    def __init__(self, **kwargs: str | bool):
        super().__init__(**kwargs)

        self.reload_service_files = bool(kwargs.get("reload_service_files", False))
        self.follow_logs = bool(kwargs.get("follow_logs", False))
