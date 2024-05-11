from __future__ import annotations

import os
import platform
import shutil
import stat

os_platform = platform.system()


#
# if os_platform == "Windows":
#     import ctypes
#     kdll = ctypes.windll.LoadLibrary("kernel32.dll")


def remove_dir(path: str, adapt_permissions: bool = True):
    if os.path.exists(path):
        if adapt_permissions:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            for root, dirs, files in os.walk(path):
                for p in dirs + files:
                    os.chmod(os.path.join(root, p), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        if os.path.islink(path):
            os.unlink(path)
        else:
            shutil.rmtree(path, ignore_errors=False)

    # https://stackoverflow.com/questions/1854/how-to-identify-which-os-python-is-running-on
    # os_platform = platform.system()
    # if os_platform == 'Linux' or os_platform == 'Darwin':
    # elif os_platform == 'Windows':


def create_dir_by_cmd(path: str, sudo=False):
    global os_platform
    if os_platform == "Linux" or os_platform == "Darwin":
        os.system(f"{'sudo ' if sudo else ''}mkdir -p {path}")
    elif os_platform == "Windows":
        raise NotImplementedError("Not implemented yet")


def create_dir_symlink(src: str, dest: str):
    global os_platform

    # Create path if it does not exist
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os_platform == "Linux" or os_platform == "Darwin" or os_platform == "Windows":
        # Check if dest already exists
        if os.path.exists(dest) or os.path.islink(dest):
            # If it is a symlink, remove it
            os.unlink(dest)

        # IMPORTANT: For windows, you must enable developer mode or run as admin
        os.symlink(src, dest)

    # Those were unnecessary on Windows, if developer mode is enabled
    # elif os_platform == 'Windows':
    #     x = kdll.CreateSymbolicLinkW(dest, src, 1)
    #     # kdll.CreateSymbolicLinkW(src, dest, 1)
    # subprocess.check_call('mklink /J "%s" "%s"' % (src, dest), shell=True)


def create_file_symlink(src: str, dest: str):
    global os_platform

    # Create path if it does not exist
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os_platform == "Linux" or os_platform == "Darwin" or os_platform == "Windows":
        # Check if dest already exists
        if os.path.exists(dest):
            # If it is a symlink, remove it
            if os.path.islink(dest):
                os.unlink(dest)

        # IMPORTANT: For windows, you must enable developer mode or run as admin
        os.symlink(src, dest)


def unlink_dir_symlink(path: str):
    if os.path.islink(path):
        os.unlink(path)
