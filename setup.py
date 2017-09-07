#!/usr/bin/python

from setuptools import setup, find_packages
from concreate.version import version

import codecs

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="concreate",
    version=version,
    packages=find_packages(exclude=["tests"]),
    package_data={
        'concreate.templates': ['*.jinja'],
        'concreate.schema': ['*.yaml'],
    },
    url='https://github.com/jboss-container-images/concreate',
    download_url="https://github.com/jboss-container-images/concreate/archive/%s.tar.gz" % version,
    author='Cloud Enablement',
    author_email='cloud-enablement-feedback@redhat.com',
    description='Containers creator',
    long_description=codecs.open('README.rst', encoding="utf8").read(),
    license='MIT',
    keywords='docker',
    entry_points={
        'console_scripts': ['concreate=concreate.cli:run'],
    },
    tests_require=['mock'],
    install_requires=requirements
)
