from dogen import tools

def artifact_fetcher_disable_ssl_check():
    tools.Artifact.ssl_verify = False
    
