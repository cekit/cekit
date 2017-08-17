from dogen import tools

from functools import partial

def artifact_fetcher_disable_ssl_check():
    tools.artifact_fetcher = partial(tools.fetch_artifact,
                                     ssl_verify = False)
    
