import hashlib
import logging

logger = logging.getLogger('cekit')

SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha1', 'md5']


def get_sum(target, algorithm):
    hash_function = getattr(hashlib, algorithm)()

    with open(target, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_function.update(chunk)
    return hash_function.hexdigest()
    

def check_sum(target, algorithm, expected, name=None):
    """ Check that file chksum is correct
    Args:
      alg - algorithm which will be used for diget
      expected_chksum - checksum which artifact must match
    """
    if not name:
        name = target
    logger.debug("Checking '%s' %s hash..." % (target, algorithm))

    checksum = get_sum(target, algorithm)

    if checksum.lower() != expected.lower():
        logger.error("The %s computed for the '%s' file ('%s') doesn't match the '%s' value"
                     % (algorithm, target, checksum, expected))
        return False

    logger.debug("Hash is correct.")
    return True
