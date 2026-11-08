"""Codejail controls for tests that execute capa problem code."""

import codejail.safe_exec
from django.test.utils import TestContextDecorator


class UseUnsafeCodejail(TestContextDecorator):
    """
    Tell codejail to run in unsafe mode for the scope of the decorator.
    Use this as a decorator on Django TestCase classes or methods.

    This is needed because codejail has significant OS-level setup requirements
    which we don't even attempt to fulfill for unit testing purposes. Running
    tests in unsafe mode (that is, running code executions in-process, with no
    sandboxing) is only safe because we control the contents of the unit tests.
    It's not a perfect replica of how safe mode operates but it's generally good
    enough for testing the integration and overall behavior.
    """

    def __init__(self):
        self.old_be_unsafe = None
        super().__init__()

    def enable(self):
        """Enable unsafe mode for codejail within the test scope."""
        self.old_be_unsafe = codejail.safe_exec.ALWAYS_BE_UNSAFE
        codejail.safe_exec.ALWAYS_BE_UNSAFE = True

    def disable(self):
        """Restore the previous codejail unsafe mode state."""
        codejail.safe_exec.ALWAYS_BE_UNSAFE = self.old_be_unsafe
