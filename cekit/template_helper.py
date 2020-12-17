import os


class TemplateHelper(object):

    SUPPORTED_PACKAGE_MANAGERS = ['yum', 'dnf', 'microdnf', 'apk']

    def __init__(self, module_registry):
        self._module_registry = module_registry

    def module(self, to_install):
        return self._module_registry.get_module(to_install.name, to_install.version, suppress_warnings=True)

    def packages_to_install(self, image):
        """
        Method that returns list of packages to be installed by any of
        modules or directly in the image
        """
        all_modules = self.modules(image)

        packages = []

        for module in all_modules:
            if 'packages' in module and 'install' in module.packages:
                packages += module.packages.install

        return packages

    def modules(self, image):
        all_modules = []

        if 'modules' in image and 'install' in image.modules:
            all_modules += [self.module(m) for m in image.modules.install]

        all_modules.append(image)

        return all_modules

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

    def all_envs(self, image):
        envs = []
        for module in self.modules(image):
            envs += module.envs

        return envs

    def all_labels(self, image):
        labels = []
        for module in self.modules(image):
            labels += module.labels

        return labels

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

    def cachito(self, image):
        if image.get('osbs', {}).get('configuration', {}).get('container', {}).get('remote_source'):
            return True
