from __future__ import annotations

import re

import gitlab
import pakk.config.pakk_config as cfg
import inspect

gl = None


def get_gitlab_instance() -> gitlab.Gitlab:
    # private token or personal token authentication (self-hosted GitLab instance)
    global gl

    if gl is not None:
        return gl

    c = cfg.get()

    # Get the signature of the object constructor
    signature = inspect.signature(gitlab.Gitlab.__init__)

    # Create dictionary with the arguments for the constructor
    init_dict = dict(c[cfg.Sections.GITLAB_CONNECTION])
    for key in set(init_dict.keys()) - set(signature.parameters.keys()):
        if key in init_dict:
            del init_dict[key]

    gl = gitlab.Gitlab(**init_dict)
    gl = gitlab.Gitlab.from_config(cfg.Sections.GITLAB_CONNECTION, cfg.get_cfg_paths())
    return gl


def get_gitlab_http_with_token(http_url_to_repo: str, token: str | None = None):
    """
    Return the http url with the token directly in the url included.
    For GitLab the form is the following: https://oauth2:{token}@{http_url}

    Parameters
    ----------
    http_url_to_repo: str
        The http url to the git repo.
    token: str
        The token to use for authentication. If None, the token from the config file is used.

    Returns
    -------
    str: The http url with the token included.

    """
    http = re.sub(r"https+://", "", http_url_to_repo)
    c = cfg.get()
    if token is None:
        token = c.get(cfg.Sections.GITLAB_CONNECTION, "private_token")
    return f"https://oauth2:{token}@{http}"
