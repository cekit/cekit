import hashlib
import logging
from typing import List

logger = logging.getLogger("cekit")

SUPPORTED_HASH_ALGORITHMS: List[str] = ["sha512", "sha256", "sha1", "md5"]
SUPPORTED_SOURCE_HASH_ALGORITHMS: List[str] = [
    "source-sha1",
    "source-sha256",
    "source-md5",
]


def get_sum(target, algorithm):
    hash_function = getattr(hashlib, algorithm)()

    logger.debug("Computing {} checksum for '{}' file".format(algorithm, target))

    with open(target, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_function.update(chunk)
    return hash_function.hexdigest()


def check_sum(target, algorithm, expected):
    """Check that file checksum is correct
    Args:
      alg - algorithm which will be used for digest
      expected_checksum - checksum which artifact must match
    """
    logger.debug("Checking '{}' {} hash...".format(target, algorithm))

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
