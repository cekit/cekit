#!/usr/bin/python

import codecs

from setuptools import find_packages, setup

from cekit.version import __version__

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="cekit",
    version=__version__,
    packages=find_packages(exclude=["tests"]),
    package_data={
        "cekit.templates": ["*.jinja"],
        "cekit.schema": ["*.yaml"],
    },
    url="https://github.com/cekit/cekit",
    download_url="https://github.com/cekit/cekit/archive/%s.tar.gz" % __version__,
    author="CEKit team",
    author_email="cekit@cekit.io",
    description="Container image creation tool",
    long_description=codecs.open("README.rst", encoding="utf-8").read(),
    license="MIT",
    entry_points={
        "console_scripts": ["cekit=cekit.cli:cli", "cekit-cache=cekit.cache.cli:cli"],
    },
    tests_require=["mock"],
    install_requires=requirements,
)
