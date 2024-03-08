import hashlib
import logging
from typing import List

from cekit.cekit_types import PathType

logger = logging.getLogger("cekit")

SUPPORTED_HASH_ALGORITHMS: List[str] = ["sha512", "sha256", "sha1", "md5"]
SUPPORTED_SOURCE_HASH_ALGORITHMS: List[str] = [
    "source-sha1",
    "source-sha256",
    "source-md5",
]


def get_sum(target: PathType, algorithm: str) -> str:
    hash_function = getattr(hashlib, algorithm)()

    logger.debug(f"Computing {algorithm} checksum for '{target}' file")

    with open(target, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_function.update(chunk)
    return hash_function.hexdigest()


def check_sum(target: PathType, algorithm: str, expected: str) -> bool:
    """Check that file checksum is correct
    Args:
      alg - algorithm which will be used for digest
      expected_checksum - checksum which artifact must match
    """
    logger.debug(f"Checking '{target}' {algorithm} hash...")

    checksum = get_sum(target, algorithm)

    if checksum.lower() != expected.lower():
        logger.error(
            "The {} computed for the '{}' file ('{}') doesn't match the '{}' value".format(
                algorithm, target, checksum, expected
            )
        )
        return False

    logger.debug("Hash is correct.")
    return True
