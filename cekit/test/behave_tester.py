import logging
import os

from cekit.builder import Command
from cekit.generator.base import Generator
from cekit.test.collector import BehaveTestCollector
from cekit.test.behave_runner import BehaveTestRunner

LOGGER = logging.getLogger('cekit')


class BehaveTester(Command):
    """
    Tester implementation for the Behave framework
    """

    def __init__(self, params):
        super(BehaveTester, self).__init__('behave', Command.TYPE_TESTER)

        self.params = params
        self.collected = False

        self.test_collector = BehaveTestCollector(os.path.dirname(self.params.descriptor), self.params.target)
        self.test_runner = BehaveTestRunner(self.params.target)

        self.generator = None

    def prepare(self):
        self.generator = Generator(self.params.descriptor,
                                   self.params.target,
                                   self.params.overrides)

        # Handle dependencies for selected generator, if any
        LOGGER.debug("Checking CEKit generate dependencies...")
        self.dependency_handler.handle(self.generator, self.params)

        self.generator.init()

        # TODO: investigate if we can improve handling different schema versions
        self.collected = self.test_collector.collect(
            self.generator.image.get('schema_version'), self.params.steps_url)

        if self.collected:
            # Handle test dependencies, if any
            LOGGER.debug("Checking CEKit test collector dependencies...")
            self.dependency_handler.handle(self.test_collector, self.params)
            LOGGER.debug("Checking CEKit test runner dependencies...")
            self.dependency_handler.handle(self.test_runner, self.params)

    def run(self):
        if not self.collected:
            LOGGER.warning("No test collected, test can't be run.")
            return

        test_tags = [self.generator.get_tags()[0]]

        # If wip is specified set tags to @wip
        if self.params.wip:
            test_tags = ['@wip']

        image = self.params.image

        if not image:
            image = self.generator.get_tags()[0]

        self.test_runner.run(image, test_tags,
                             test_names=self.params.names)
