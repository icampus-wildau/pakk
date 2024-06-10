from __future__ import annotations

VERSION_DELIMITER = ["@", "==", "="]


def split_name_version(name: str) -> tuple[str, str | None]:
    """
    Split the name and version of a package name.
    Possible delimiters defined in VERSION_DELIMITER array.
    """

    for d in VERSION_DELIMITER:
        if d in name:
            splits = name.split(d)
            return splits[0], splits[1]

    return name, None
