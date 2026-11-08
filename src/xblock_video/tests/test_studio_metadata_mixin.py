"""Tests for StudioMetadataMixin.editable_metadata_fields (VideoBlock)."""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test.utils import override_settings
from opaque_keys.edx.locator import CourseLocator
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds

from xblock_video.block import VideoBlock
from xblock_video.exceptions import TranscriptNotFoundError
from xblock_video.tests.test_utils import DummyRuntime

ALL_LANGUAGES = (
    ("en", "English"),
    ("eo", "Esperanto"),
    ("ur", "Urdu"),
)


@override_settings(ALL_LANGUAGES=ALL_LANGUAGES)
class TestEditableMetadataFieldsProperty(SimpleTestCase):
    """
    Unit tests for VideoBlock.editable_metadata_fields property.

    The property enriches the raw editable fields returned by
    _get_editable_metadata_fields with video-specific customisations:
    transcript language lists, special types for certain fields, etc.
    """

    @staticmethod
    def _instantiate_block(**field_data):
        """Instantiate a VideoBlock with a DummyRuntime."""
        system = DummyRuntime()
        course_key = CourseLocator("org", "course", "run")
        usage_key = course_key.make_usage_key("video", "SampleProblem")
        return system.construct_xblock_from_class(
            VideoBlock,
            scope_ids=ScopeIds(None, None, usage_key, usage_key),
            field_data=DictFieldData(field_data),
        )

    def setUp(self):
        super().setUp()
        self.block = self._instantiate_block()

    def _base_fields(self, include_license=True):
        """Return a minimal editable-fields dict that satisfies the property's expectations."""
        fields = {
            "sub": {"type": "Generic", "value": ""},
            "transcripts": {"type": "Dict", "value": {}},
            "edx_video_id": {"type": "Generic", "value": ""},
            "public_access": {"type": "Select", "value": False},
            "handout": {"type": "Generic", "value": ""},
        }
        if include_license:
            fields["license"] = {"type": "License", "value": ""}
        return fields

    @staticmethod
    def _service_stub(service_name, service_obj):
        """Return a runtime.service stub that serves service_obj only for service_name."""
        return lambda _block, name: service_obj if name == service_name else None

    def _get_fields(self, include_license=False, public_url=None, transcripts=None, service=None):
        """
        Call editable_metadata_fields with standard mocks applied.

        Pass service=<callable> to simulate a real runtime service (e.g. for
        licensing or video_config tests); omit it to have all service calls
        return None (skipping license and English-transcript logic).
        """
        service_kwargs = {"side_effect": service} if service else {"return_value": None}
        with (
            patch.object(self.block, "_get_editable_metadata_fields", return_value=self._base_fields(include_license)),
            patch.object(
                self.block,
                "get_transcripts_info",
                return_value={"sub": self.block.sub, "transcripts": transcripts or {}},
            ),
            patch.object(self.block, "get_public_video_url", return_value=public_url),
            patch.object(self.block.runtime, "service", **service_kwargs),
        ):
            return self.block.editable_metadata_fields

    # ------------------------------------------------------------------
    # Field-level modifications
    # ------------------------------------------------------------------

    def test_default_field_modifications(self):
        """Verify all field-level changes made by editable_metadata_fields with default args."""
        fields = self._get_fields()
        self.assertNotIn("sub", fields)
        self.assertTrue(fields["transcripts"]["custom"])
        self.assertEqual(fields["transcripts"]["type"], "VideoTranslations")
        self.assertEqual(
            fields["transcripts"]["languages"],
            [
                {"label": "English", "code": "en"},
                {"label": "Esperanto", "code": "eo"},
                {"label": "Urdu", "code": "ur"},
            ],
        )
        # DummyRuntime.handler_url returns a fixed path used by the transcript upload widget
        self.assertEqual(fields["transcripts"]["urlRoot"], "/handler/block/handler")
        self.assertEqual(fields["edx_video_id"]["type"], "VideoID")
        self.assertEqual(fields["handout"]["type"], "FileUploader")
        # public_access type is always set; url is None when no public video URL is available
        self.assertEqual(fields["public_access"]["type"], "PublicAccess")
        self.assertIsNone(fields["public_access"]["url"])

    def test_transcripts_value_passthrough(self):
        """Verify transcripts.value is passed through from get_transcripts_info."""
        fields = self._get_fields(transcripts={"fr": "french.srt"})
        self.assertEqual(fields["transcripts"]["value"], {"fr": "french.srt"})

    def test_public_access_enriched_when_url_present(self):
        """Verify public_access url is populated when a public video URL is available."""
        fields = self._get_fields(public_url="https://example.com/video")
        self.assertEqual(fields["public_access"]["type"], "PublicAccess")
        self.assertEqual(fields["public_access"]["url"], "https://example.com/video")

    # ------------------------------------------------------------------
    # License field handling
    # ------------------------------------------------------------------

    def test_license_removed_when_licensing_disabled(self):
        """'license' is removed when the settings service reports licensing_enabled=False."""
        settings_service = Mock()
        settings_service.get_settings_bucket.return_value = {"licensing_enabled": False}
        fields = self._get_fields(
            include_license=True,
            service=self._service_stub("settings", settings_service),
        )
        self.assertNotIn("license", fields)

    def test_license_kept_when_licensing_enabled(self):
        """'license' is kept when the settings service reports licensing_enabled=True."""
        settings_service = Mock()
        settings_service.get_settings_bucket.return_value = {"licensing_enabled": True}
        fields = self._get_fields(
            include_license=True,
            service=self._service_stub("settings", settings_service),
        )
        self.assertIn("license", fields)

    def test_license_retained_when_no_settings_service(self):
        """'license' is retained when no settings service is available (service returns None)."""
        fields = self._get_fields(include_license=True)
        self.assertIn("license", fields)

    # ------------------------------------------------------------------
    # English transcript lookup via video_config service
    # ------------------------------------------------------------------

    def test_english_transcript_found_added_to_value(self):
        """When video_config returns an English transcript, it is added to transcripts.value."""
        video_config = Mock()
        video_config.get_transcript.return_value = ("content", "en_subs_id", "txt")
        fields = self._get_fields(
            transcripts={},
            service=self._service_stub("video_config", video_config),
        )
        self.assertEqual(fields["transcripts"]["value"], {"en": "en_subs_id"})

    def test_english_transcript_merged_with_existing_transcripts(self):
        """English transcript from video_config is merged with, not replacing, existing transcripts."""
        video_config = Mock()
        video_config.get_transcript.return_value = ("content", "en_subs_id", "txt")
        fields = self._get_fields(
            transcripts={"fr": "french.srt"},
            service=self._service_stub("video_config", video_config),
        )
        self.assertEqual(fields["transcripts"]["value"], {"fr": "french.srt", "en": "en_subs_id"})

    def test_transcript_not_found_leaves_value_unchanged(self):
        """When video_config raises TranscriptNotFoundError, transcripts.value is not modified."""
        video_config = Mock()
        video_config.get_transcript.side_effect = TranscriptNotFoundError
        fields = self._get_fields(
            transcripts={"fr": "french.srt"},
            service=self._service_stub("video_config", video_config),
        )
        self.assertNotIn("en", fields["transcripts"]["value"])
        self.assertEqual(fields["transcripts"]["value"], {"fr": "french.srt"})
