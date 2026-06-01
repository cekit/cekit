import logging
import os
import yaml
LOGGER = logging.getLogger("cekit")

from cekit.template_helper import TemplateHelper
from cekit.generator.base import Generator
from cekit.cekit_types import PathType
from typing import TYPE_CHECKING, Callable, Dict, List

from cekit.tools import get_skopeo_inspect_json, split_image_name_ref

class KonfluxGenerator(Generator):
    def prepare_artifacts(self) -> None:
        LOGGER.debug("KonfluxGenerator prepare_artifacts")

        for image in self.images:
            for artifact in image.all_artifacts:
                raise NotImplementedError("Artifacts handling is not implemented")

    def generate(self) -> None:
        self._resolve_floating_parent_image()
        super(KonfluxGenerator, self).generate()
        self._render_rpm_lockfile()

    def _render_rpm_lockfile(self) -> None:
        y = self.image.get("konflux",{}).get("rpms.in.yaml", {})
        if not y:
            return

        y['packages'] = self._populate_packages()

        f = os.path.join(self.target, "image", "rpms.in.yaml")
        with open(f, "w") as fh:
            yaml.safe_dump(y, fh, default_flow_style=False)

    def _populate_packages(self) -> None:
        th = TemplateHelper(self._module_registry)
        pkgs = list(set(th.packages_to_install(self.image)))
        pkgs.sort()
        return pkgs

    def _resolve_floating_parent_image(self) -> None:
        """
        Replace the FROM image tag/digest specification (if any) with the
        Manifest List Digest that it current resolves to.
        """
        # we don't worry about from: in any modules (see #958)
        (frm, tag) = split_image_name_ref(self.image['from'])
        LOGGER.debug("KonfluxGenerator._resolve_floating_parent_image: {}, {}".format(frm,tag))
        image_json = get_skopeo_inspect_json(frm)
        digest = image_json['Digest']
        LOGGER.debug("KonfluxGenerator._resolve_floating_parent_image: digest is {}".format(digest))
        self.image['from'] = frm + "@" + digest
