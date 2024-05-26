from __future__ import annotations

import logging
import os
import re

from git import Repo

from pakk.args.base_args import BaseArgs
from pakk.logger import Logger

logger = logging.getLogger(__name__)


def dev(path: str, **kwargs: str):
    if path is None or len(path) == 0:
        # Get current working directory
        path = os.getcwd()

    logger.info(f"Switch to dev mode in: {path}")

    # Get the repo
    repo = Repo(path)

    # If not on a branch
    active_branch = None
    try:
        active_branch = repo.active_branch
    except TypeError:
        pass

    if active_branch is None:
        # Adapt origin url by removing the access token
        origin = repo.remotes.origin
        origin_url = origin.url
        old_origin_url = origin_url

        pattern = re.compile(r"https+://([^@]*@).*")
        match = pattern.match(origin_url)
        if match is not None:
            origin_url = origin_url.replace(match.group(1), "")
            origin.set_url(origin_url)
            logger.info(f"Adapter origin url from `{old_origin_url}` to `{origin_url}`")

        # Adapt the fetch config
        repo.config_writer(config_level="repository").set_value(
            'remote "origin"', "fetch", "+refs/heads/*:refs/remotes/origin/*"
        )

        # Fetch
        origin = repo.remotes.origin
        origin.fetch()

        # Get the remote branches
        remote_branches = repo.remotes.origin.refs
        logger.info(f"Found {len(remote_branches)} remote branches:")
        logger.info(remote_branches)

        if len(remote_branches) == 0:
            logger.warning("No remote branches")
            return

        # Checkout the first remote branch
        remote_branch = remote_branches[0]
        logger.info("Checkout remote branch: " + remote_branch.name)

        local_branch_name = remote_branch.name.replace("origin/", "")

        # Check if local branch already exists
        branches = repo.branches
        if local_branch_name not in branches:
            repo.git.checkout("-b", local_branch_name, remote_branch.name)
        else:
            repo.git.checkout(local_branch_name)
            repo.git.branch(f"--set-upstream-to={remote_branch.name}", local_branch_name)
        repo.git.pull()

    else:
        logger.info(f"Already on branch: {active_branch.name}")
        return
