import logging
import os

from cekit.errors import CekitError
from cekit.tools import Chdir

try:
    from behave.__main__ import main as behave_main
except ModuleNotFoundError:
    pass

logger = logging.getLogger("cekit")


class BehaveTestRunner(object):
    def __init__(self, target):
        self.target = os.path.abspath(target)

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps["python-behave"] = {
            "library": "behave",
            "package": "python3-behave",
        }

        return deps

    def run(self, image, run_tags, test_names, include_regex, exclude_regex):
        """Run test suite"""
        test_path = os.path.join(self.target, "test")
        logger.debug(f"Running behave in '{test_path}'.")
        args = [
            test_path,
            "--junit",
            "--junit-directory",
            "results",
            "--no-skipped",
            "-t",
            "~ignore",
            "-D",
            f"IMAGE={image}",
        ]

        if test_names:
            for name in test_names:
                args.append("--name")
                args.append(f"{name}")
        else:
            for tag in run_tags:
                # Remove anything after the colon, typically the docker tag.
                tag = tag.partition(":")[0]

                args.append("-t")
                if "/" in tag:
                    args.append(f"@{tag.split('/')[0]},@{tag}")
                else:
                    args.append(tag)

        if include_regex:
            args.append("-i")
            args.append(f"{include_regex}")

        if exclude_regex:
            args.append("-e")
            args.append(f"{exclude_regex}")

        logger.debug(f"Running behave tests with args '{args}'.")

        try:
            with Chdir(os.path.join(self.target, "test")):
                logger.debug(f"behave args: {args}")
                if behave_main(args) != 0:
                    raise CekitError(
                        "Test execution failed, please consult output above"
                    )
        except CekitError:
            raise
        except Exception:
            raise CekitError("An error occurred while executing tests")
