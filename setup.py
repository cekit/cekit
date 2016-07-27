#!/usr/bin/python

from setuptools import setup, find_packages
from dogen.version import version

import codecs

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name = "dogen",
    version = version,
    packages = find_packages(exclude=["tests"]),
    package_data = {
        'dogen.templates': ['*.jinja'],
        'dogen.schema': ['*.yaml'],
        'dogen.plugins.cct': ['*.yaml'],
    },
    url = 'https://github.com/jboss-dockerfiles/dogen',
    download_url = "https://github.com/jboss-dockerfiles/dogen/archive/%s.tar.gz" % version,
    author = 'Cloud Enablement',
    author_email = 'cloud-enablement-feedback@redhat.com',
    description = 'Dockerfile generator tool',
    license='MIT',
    keywords = 'docker',
    long_description = codecs.open('README.rst', encoding="utf8").read(),
    entry_points = {
        'console_scripts': ['dogen=dogen.cli:run'],
    },
    tests_require = ['mock'],
    install_requires=requirements
)
