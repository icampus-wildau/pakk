from __future__ import annotations

from pakk.args.base_args import BaseArgs


class UpdateStrategy:
    EAGER = "eager"
    ONLY_IF_NEEDED = "only_if_needed"


class InstallArgs(BaseArgs):
    def __init__(self, **kwargs: str | bool):
        super().__init__(**kwargs)

        self.force_reinstall: bool = bool(kwargs.get("force_reinstall", False))
        self.upgrade: bool = bool(kwargs.get("upgrade", False))
        self.upgrade_strategy: str = str(kwargs.get("upgrade_strategy", UpdateStrategy.EAGER))
        self.allow_downgrade: bool = bool(kwargs.get("allow_downgrade", False))
        self.no_deps: bool = bool(kwargs.get("no_deps", False))
        self.dry_run: bool = bool(kwargs.get("dry_run", False))
        self.refetch: bool = bool(kwargs.get("refetch", False))
        self.ignore_installed: bool = bool(kwargs.get("ignore_installed", False))
        self.clear_cache: bool = bool(kwargs.get("clear_cache", False))
        self.repair: bool = bool(kwargs.get("repair", False))
