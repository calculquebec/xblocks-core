"""Test utilities for the video XBlock: DummyRuntime, AsideTestType, and constants."""

from unittest.mock import Mock

from web_fragments.fragment import Fragment
from xblock.core import XBlockAside
from xblock.fields import Scope, String
from xblock.runtime import DictKeyValueStore, KvsFieldData, Runtime
from xblock.test.tools import TestRuntime

EXPORT_IMPORT_STATIC_DIR = "static"
VALIDATION_MESSAGE_WARNING = "warning"


class DummyRuntime(TestRuntime, Runtime):
    """
    Construct a test DummyRuntime instance.
    """

    def __init__(self, _render_template=None, **kwargs):
        services = kwargs.setdefault("services", {})
        services["field-data"] = KvsFieldData(DictKeyValueStore())
        video_config_mock = Mock(name="video_config")
        video_config_mock.available_translations = lambda block, transcripts_info, verify_assets=True: []
        services["video_config"] = video_config_mock

        # Ignore load_error_blocks as it's not supported by modern TestRuntime
        kwargs.pop("load_error_blocks", None)

        super().__init__(**kwargs)
        self._resources_fs = Mock(name="DummyRuntime.resources_fs", root_path=".")

    def handler_url(self, *args, **kwargs):
        """Return a test handler URL."""
        return "/handler/block/handler"

    def local_resource_url(self, *args, **kwargs):
        """Return a test local resource URL."""
        return "/resource/"

    def publish(self, *args, **kwargs):
        """No-op for tests."""
        return None

    def query(self, block):
        """Return a mock query for tests."""
        return Mock()

    def resource_url(self, *args, **kwargs):
        """Return a test resource URL."""
        return "/static/"

    def parse_asides(self, node, def_id, usage_id, _id_generator):
        """pull the asides out of the xml payload and instantiate them"""
        aside_children = []
        for child in node.iterchildren():
            # get xblock-family from node
            xblock_family = child.attrib.pop("xblock-family", None)
            if xblock_family:
                xblock_family = self._family_id_to_superclass(xblock_family)
                if issubclass(xblock_family, XBlockAside):
                    aside_children.append(child)
        # now process them & remove them from the xml payload
        for child in aside_children:
            self._aside_from_xml(child, def_id, usage_id)
            node.remove(child)
        return aside_children

    @property
    def resources_fs(self):
        return self._resources_fs


class AsideTestType(XBlockAside):
    """
    Test Aside type
    """

    FRAG_CONTENT = "<p>Aside rendered</p>"

    content = String(default="default_content", scope=Scope.content)
    data_field = String(default="default_data", scope=Scope.settings)

    @XBlockAside.aside_for("student_view")
    def student_view_aside(self, block, context):  # pylint: disable=unused-argument
        """Add to the student view"""
        return Fragment(self.FRAG_CONTENT)
