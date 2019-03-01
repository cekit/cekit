import logging
import os

from cekit.builder import Command
from cekit.generator.base import Generator
from cekit.test.collector import TestCollector
from cekit.test.runner import TestRunner

LOGGER = logging.getLogger('cekit')


class BehaveTester(Command):
    """
    Tested implementation for the Behave framework
    """

    def __init__(self, common_params, params):
        super(BehaveTester, self).__init__('behave', Command.TYPE_TESTER)

        self.common_params = common_params
        self.params = params
        self.collected = False

        self.test_collector = TestCollector(os.path.dirname(self.common_params.descriptor),
                                            self.common_params.target)

        self.generator = None

    def prepare(self):
        self.generator = Generator(self.common_params.descriptor,
                                   self.common_params.target,
                                   self.params.overrides)

        # Handle dependencies for selected generator, if any
        LOGGER.debug("Checking CEKit generate dependencies...")
        self.dependency_handler.handle(self.generator)

        self.generator.init()

        # TODO: investigate if we can improve handling different schema versions
        self.collected = self.test_collector.collect(
            self.generator.image.get('schema_version'), self.params.steps_url)

        if self.collected:
            # Handle test dependencies, if any
            LOGGER.debug("Checking CEKit test dependencies...")
            self.dependency_handler.handle(self.test_collector)

    def run(self):
        if not self.collected:
            LOGGER.warning("No test collected, test can't be run.")
            return

        test_tags = [self.generator.get_tags()[0]]

        # If wip is specified set tags to @wip
        if self.params.wip:
            test_tags = ['@wip']

        runner = TestRunner(self.common_params.target)
        runner.run(self.params.image, test_tags,
                   test_names=self.params.names)
