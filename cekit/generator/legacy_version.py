#
# This is a heavily streamlined subset of https://github.com/pypa/packaging/blob/21.3/packaging/version.py to extract
# LegacyVersion that was dropped in version 22.
#
# SPDX-license-identifier: BSD-2-Clause or Apache-2.0
# copyright (c) Donald Stufft and individual contributors
#
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See
# https://github.com/pypa/packaging/blob/21.3/LICENSE.APACHE
# https://github.com/pypa/packaging/blob/21.3/LICENSE.BSD

import re
from typing import Iterator, List, Tuple, Union

from packaging.version import CmpKey, _BaseVersion

LegacyCmpKey = Tuple[int, Tuple[str, ...]]


class _MyBaseVersion(_BaseVersion):
    _key: Union[CmpKey, LegacyCmpKey]


class LegacyVersion(_MyBaseVersion):
    @staticmethod
    def _parse_version_parts(s: str) -> Iterator[str]:
        _legacy_version_component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE)
        _legacy_version_replacement_map = {
            "pre": "c",
            "preview": "c",
            "-": "final-",
            "rc": "c",
            "dev": "@",
        }
        for part in _legacy_version_component_re.split(s):
            part = _legacy_version_replacement_map.get(part, part)

            if not part or part == ".":
                continue

            if part[:1] in "0123456789":
                # pad for numeric comparison
                yield part.zfill(8)
            else:
                yield "*" + part
        # ensure that alpha/beta/candidate are before final
        yield "*final"

    @staticmethod
    def _legacy_cmpkey(version: str) -> LegacyCmpKey:
        # We hardcode an epoch of -1 here. A PEP 440 version can only have a epoch
        # greater than or equal to 0. This will effectively put the LegacyVersion,
        # which uses the defacto standard originally implemented by setuptools,
        # as before all PEP 440 versions.
        epoch = -1

        # This scheme is taken from pkg_resources.parse_version setuptools prior to
        # it's adoption of the packaging library.
        parts: List[str] = []
        for part in LegacyVersion._parse_version_parts(version.lower()):
            if part.startswith("*"):
                # remove "-" before a prerelease tag
                if part < "*final":
                    while parts and parts[-1] == "*final-":
                        parts.pop()

                # remove trailing zeros from each series of numeric parts
                while parts and parts[-1] == "00000000":
                    parts.pop()

            parts.append(part)

        return epoch, tuple(parts)

    def __init__(self, version: str) -> None:
        self._version = str(version)
        self._key = LegacyVersion._legacy_cmpkey(self._version)

    def __str__(self) -> str:
        return self._version

    def __repr__(self) -> str:
        return f"<LegacyVersion('{self}')>"

    @property
    def public(self) -> str:
        return self._version

    @property
    def base_version(self) -> str:
        return self._version

    @property
    def epoch(self) -> int:
        return -1

    @property
    def release(self) -> None:
        return None

    @property
    def pre(self) -> None:
        return None

    @property
    def post(self) -> None:
        return None

    @property
    def dev(self) -> None:
        return None

    @property
    def local(self) -> None:
        return None

    @property
    def is_prerelease(self) -> bool:
        return False

    @property
    def is_postrelease(self) -> bool:
        return False

    @property
    def is_devrelease(self) -> bool:
        return False


def parse(version: str) -> "LegacyVersion":
    """
    Parse the given version string and return a :class:`LegacyVersion` object
    """
    return LegacyVersion(version)
