import os
import re


class TemplateHelper(object):

    def filename(self, source):
        """Simple helper to return the file specified name"""

        target = source.get('target')

        if target:
            return target

        return os.path.basename(source['artifact'])

    def cmd(self, arr):
        """Generates array of commands that could be used like this:
        CMD {{ helper.cmd(cmd) }}
        """

        ret = []
        for cmd in arr:
            ret.append("\"%s\"" % cmd)
        return "[%s]" % ', '.join(ret)

    def envs(self, env_variables):
        """Combines all environment variables that should be added to the
        Dockerfile into one array
        """

        envs = []

        for env in env_variables:
            if env.get('value') is not None:
                envs.append(env)

        return envs

    def ports(self, available_ports):
        """
        Combines all ports that should be added to the
        Dockerfile into one array
        """

        port_list = []

        for p in available_ports:
            if p.get('expose', True):
                port_list.append(p.get('value'))

        return port_list
