#!/usr/bin/python

from setuptools import setup, find_packages
from cekit.version import version

import codecs

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="cekit",
    version=version,
    packages=find_packages(exclude=["tests"]),
    package_data={
        'cekit.templates': ['*.jinja'],
        'cekit.schema': ['*.yaml'],
    },
    url='https://github.com/cekit/cekit',
    download_url="https://github.com/cekit/cekit/archive/%s.tar.gz" % version,
    author='Cekit team',
    author_email='cekit@cekit.io',
    description='Containers creator',
    long_description=codecs.open('README.rst', encoding="utf8").read(),
    license='MIT',
    entry_points={
        'console_scripts': ['cekit=cekit.cli:run',
                            'cekit-cache=cekit.cache.cli:run'],
    },
    tests_require=['mock'],
    install_requires=requirements
)
