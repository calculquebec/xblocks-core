"""
Unit test harness for Problem Block in xblocks-core.
"""

import pprint
from unittest.mock import MagicMock, Mock

from django.conf import settings
from opaque_keys.edx.locator import CourseLocator
from path import Path as path
from requests.auth import HTTPBasicAuth
from xblock.reference.user_service import UserService, XBlockUser
from xblock.test.tools import TestRuntime

from xblock_problem.capa.xqueue_interface import XQueueInterface

# Location of common test DATA directory
DATA_DIR = path(__file__).dirname() / "data"


def mock_render_template(*args, **kwargs):
    """
    Pretty-print the args and kwargs.

    Allows us to not depend on any actual template rendering mechanism,
    while still returning a unicode object
    """
    return pprint.pformat((args, kwargs)).encode().decode()


class DoNothingCache:
    """A duck-compatible object to use in ModuleSystemShim when there's no cache."""

    def get(self, _key):
        """Return None for any requested cache key."""
        return None

    def set(self, key, value, timeout=None):
        """Ignore cache set calls and store nothing."""


class CacheService:
    """
    An XBlock service which provides a cache.

    Args:
        cache(object): provides get/set functions for retrieving/storing key/value pairs.
    """

    def __init__(self, cache, **kwargs):
        super().__init__(**kwargs)
        self._cache = cache

    def get(self, key, *args, **kwargs):
        """Returns the value cached against the given key, or None."""
        return self._cache.get(key, *args, **kwargs)

    def set(self, key, value, *args, **kwargs):
        """Caches the value against the given key."""
        return self._cache.set(key, value, *args, **kwargs)


class StubUserService(UserService):
    """Stub UserService for testing the sequence block."""

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        user=None,
        user_is_staff=False,
        user_role=None,
        anonymous_user_id=None,
        deprecated_anonymous_user_id=None,
        request_country_code=None,
        **kwargs,
    ):
        self.user = user
        self.user_is_staff = user_is_staff
        self.user_role = user_role
        self.anonymous_user_id = anonymous_user_id
        self.deprecated_anonymous_user_id = deprecated_anonymous_user_id
        self.request_country_code = request_country_code
        self._django_user = user
        super().__init__(**kwargs)

    def get_current_user(self):
        """Implements abstract method for getting the current user."""
        user = XBlockUser()
        if self.user and self.user.is_authenticated:
            user.opt_attrs["edx-platform.anonymous_user_id"] = self.anonymous_user_id
            user.opt_attrs["edx-platform.deprecated_anonymous_user_id"] = self.deprecated_anonymous_user_id
            user.opt_attrs["edx-platform.request_country_code"] = self.request_country_code
            user.opt_attrs["edx-platform.user_is_staff"] = self.user_is_staff
            user.opt_attrs["edx-platform.user_id"] = self.user.id
            user.opt_attrs["edx-platform.user_role"] = self.user_role
            user.opt_attrs["edx-platform.username"] = self.user.username
        else:
            user.opt_attrs["edx-platform.username"] = "anonymous"
            user.opt_attrs["edx-platform.request_country_code"] = self.request_country_code
            user.opt_attrs["edx-platform.is_authenticated"] = False
        return user

    def get_user_by_anonymous_id(self, uid=None):  # pylint: disable=unused-argument
        """Return the original user passed into the service."""
        return self.user


class StubReplaceURLService:
    """Stub ReplaceURLService for testing blocks."""

    def replace_urls(self, text, static_replace_only=False):  # pylint: disable=unused-argument
        """Invokes the configured render_template method."""
        return text


class StubSandboxService:
    """Stub SandboxService for Capa/Problem blocks."""

    def can_execute_unsafe_code(self):
        return False

    def get_python_lib_zip(self):
        return None


class StubXQueueService:
    """
    Stubs out the XQueueService for Capa problem tests, aligned with Django settings.
    """

    def __init__(self):
        """Initialize the stubbed XQueueService instance."""
        basic_auth = settings.XQUEUE_INTERFACE.get("basic_auth")
        requests_auth = HTTPBasicAuth(*basic_auth) if basic_auth else None

        self.interface = XQueueInterface(
            settings.XQUEUE_INTERFACE["url"],
            settings.XQUEUE_INTERFACE["django_auth"],
            requests_auth,
            block=MagicMock(),
            use_submission_service=False,
        )
        self.default_queuename = "testqueue"

        self.waittime = getattr(settings, "XQUEUE_WAITTIME_BETWEEN_REQUESTS", 5)

    def construct_callback(self, dispatch="score_update"):
        """A callback url method to use in tests."""
        return dispatch


class TestDescriptorSystem(TestRuntime):
    """
    Custom runtime that mimics ModuleStoreRuntime's interface for testing,
    but sits on top of the standard XBlock TestRuntime.
    """

    def __init__(self, services=None, render_template=None, **kwargs):
        super().__init__(services=services, **kwargs)
        self._render_template_func = render_template or mock_render_template

    # Minimal implementations to satisfy abstract methods
    def query(self, *args, **kwargs):  # pylint: disable=unused-argument
        """Satisfy abstract method."""
        return None

    def resource_url(self, *args, **kwargs):
        """Satisfy abstract method."""
        return ""

    def handler_url(  # pylint: disable=arguments-differ,unused-argument
        self, block, handler_name, suffix="", query="", thirdparty=False
    ):
        """Mock handler URL generation to look like edx-platform URLs."""
        return f"http://testserver/xblock/{block.usage_key}/{handler_name}/{suffix}?{query}"

    def local_resource_url(self, block, uri):  # pylint: disable=arguments-differ
        """Mock local resource URL generation."""
        return f"resource/{block.usage_key}/{uri}"

    def publish(self, block, event_type, event_data):  # pylint: disable=arguments-differ,unused-argument
        return None

    def render_template(self, template_name, context):
        """Mirror the ModuleStoreRuntime render_template method."""
        return self._render_template_func(template_name, context)

    def resources_fs(self):
        """Mirror the ModuleStoreRuntime filesystem accessor."""
        return Mock(name="TestRuntime.resources_fs", root_path=".")


def get_test_system(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    course_id=CourseLocator("org", "course", "run"),  # noqa: B008  # pylint: disable=unused-argument
    user=None,
    user_is_staff=False,
    user_location=None,
    render_template=None,
    add_get_block_overrides=False,
):
    """
    Construct a test system instance for the Problem XBlock.
    """

    if not user:
        user = Mock(name="get_test_system.user")
        user.is_authenticated = True
        user.is_staff = user_is_staff
        user.id = "test-user-id"
        user.username = "test-user"

    if not user_location:
        user_location = Mock(name="get_test_system.user_location")

    user_service = StubUserService(
        user=user,
        anonymous_user_id="student",
        deprecated_anonymous_user_id="student",
        user_is_staff=user_is_staff,
        user_role="student",
        request_country_code=user_location,
    )

    replace_urls_service = StubReplaceURLService()
    sandbox_service = StubSandboxService()
    cache_service = CacheService(DoNothingCache())
    xqueue_service = StubXQueueService()

    services = {
        "user": user_service,
        "replace_urls": replace_urls_service,
        "cache": cache_service,
        "sandbox": sandbox_service,
        "xqueue": xqueue_service,
    }

    descriptor_system = TestDescriptorSystem(
        services=services, render_template=render_template, id_reader=Mock(name="id_reader")
    )

    if add_get_block_overrides:

        def get_block(block):
            """Mocks module_system get_block function"""
            block.runtime = descriptor_system
            return block

        descriptor_system.get_block_for_descriptor = get_block  # pylint: disable=attribute-defined-outside-init

    return descriptor_system
