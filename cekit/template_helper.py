import os


class TemplateHelper(object):

    SUPPORTED_PACKAGE_MANAGERS = ["yum", "dnf", "microdnf", "apk", "apt-get"]

    def __init__(self, module_registry):
        self._module_registry = module_registry

    def module(self, to_install):
        return self._module_registry.get_module(
            to_install.name, to_install.version, suppress_warnings=True
        )

    def packages_to_install(self, image):
        """
        Method that returns list of packages to be installed by any of
        modules or directly in the image
        """
        all_modules = self.modules(image)

        packages = []

        for module in all_modules:
            if "packages" in module and "install" in module.packages:
                packages += module.packages.install

        return packages

    def modules(self, image):
        all_modules = []

        if "modules" in image and "install" in image.modules:
            all_modules += [self.module(m) for m in image.modules.install]

        all_modules.append(image)

        return all_modules

    def filename(self, source):
        """Simple helper to return the file specified name"""

        target = source.get("target")

        if target:
            return target

        return os.path.basename(source["artifact"])

    def cmd(self, arr):
        """Generates array of commands that could be used like this:
        CMD {{ helper.cmd(cmd) }}
        """

        ret = []
        for cmd in arr:
            ret.append('"%s"' % cmd)
        return "[%s]" % ", ".join(ret)

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
            if p.get("expose", True):
                port_list.append(p.get("value"))

        return port_list

    def cachito(self, image):
        if (
            image.get("osbs", {})
            .configuration.get("container", {})
            .get("remote_source")
        ):
            return True

    def extra_dir(self, image):
        return image.get("osbs", {}).extra_dir

    def extra_dir_target(self, image):
        return image.get("osbs", {}).extra_dir_target

    def package_manager_flags(self, pkg_mgr, pkg_mgr_flags):
        if pkg_mgr_flags is not None:
            # Using None check to allow a definition of "manager_flags: ''" to override the default values.
            return pkg_mgr_flags
        elif "apk" in pkg_mgr:
            return ""
        elif "apt-get" in pkg_mgr:
            #
            # This is a HACK...
            #
            # Debian based apt-get needs an *update* step
            # *before* its "install" step...
            #
            # We really *should* add an additional step to the
            # main template repo_install and pkg_install macros
            #
            # However this works at the moment...
            #
            return "update && apt-get --no-install-recommends"

        default = "--setopt=tsflags=nodocs"
        if "microdnf" in pkg_mgr:
            return "--setopt=install_weak_deps=0 " + default
        else:
            return default

    def package_manager_install(self, pkg_mgr):
        if "apk" in pkg_mgr:
            return "add"
        else:
            return "install -y"

    def package_manager_query(self, pkg_mgr):
        if "apk" in pkg_mgr:
            return "apk info -e"
        elif "apt-get" in pkg_mgr:
            return "dpkg-query --list"
        else:
            return "rpm -q"
