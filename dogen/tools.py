import logging
import os
import requests
import subprocess
import urllib

from dogen.errors import DogenError


logger = logging.getLogger("dogen")


def fetch_artifact(url, directory=os.getcwd(), ssl_verify=True):
    destination = os.path.join(directory, os.path.basename(url))
    logger.debug("Fetching '%s' as %s" % (url, destination))

    res = requests.get(url, verify=ssl_verify, stream=True)
    if res.status_code != 200:
        raise DogenError("Could not download file from %s" % url)
    with open(destination, 'wb') as f:
        for chunk in res.iter_content(chunk_size=1024):
            f.write(chunk)
    return destination


artifact_fetcher = fetch_artifact
