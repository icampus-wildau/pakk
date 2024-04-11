# https://click.palletsprojects.com/en/8.1.x/setuptools/
# https://pymbook.readthedocs.io/en/latest/click.html
# 
# setup.py file to easy use the python module for command line
# it is recommended to write command line tools in python then directly using shebang based scripts
#
# TODO read documentation
import setuptools

setuptools.setup(
    name='pakk',
    version='0.1.0',
    py_modules=['cli'],
    install_requires=[
        'click',
        'click-aliases',
        'prettytable',
        'python-gitlab>=3.0.0',
        'networkx',
        'node-semver',
        'graphviz',
        'jsons', # Does not work for Python3.11 any more
        # 'jsons @ https://github.com/vschroeter/jsons.git',
        'semver',
        'tqdm',
        'pyfiglet',
        'rich',
        'InquirerPy',
        'python-dotenv',
        'braceexpand',
        'jellyfish',
        'flock',
        'mdplus @ git+https://icampusnet.th-wildau.de/ros-e/software/infrastructure/markdown-plus.git'
    ],
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'pakk=pakk.cli:cli',
        ],
    },
)