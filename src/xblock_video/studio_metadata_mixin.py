"""Studio Metadata Mixin"""

from django.conf import settings
from xblock.core import XBlock
from xblock.fields import Dict, Float, Integer, List, Scope, String

from .exceptions import TranscriptNotFoundError
from .video_transcripts_utils import TranscriptExtensions, get_html5_ids
from .video_xfields import RelativeTime


class StudioMetadataMixin:
    """
    Mixin providing Studio metadata editing capabilities for XBlocks.
    """

    @property
    def non_editable_metadata_fields(self):
        """
        Return the list of fields that should not be editable in Studio.

        When overriding, be sure to append to the superclasses' list.
        """
        # We are not allowing editing of xblock tag and name fields at this time (for any component).
        return [XBlock.tags, XBlock.name]

    def _create_metadata_editor_info(self, field):
        """
        Creates the information needed by the metadata editor for a specific field.
        """

        def jsonify_value(field, json_choice):
            """
            Convert field value to JSON, if needed.
            """
            if isinstance(json_choice, dict):
                new_json_choice = dict(json_choice)  # make a copy so below doesn't change the original
                if "display_name" in json_choice:
                    new_json_choice["display_name"] = get_text(json_choice["display_name"])
                if "value" in json_choice:
                    new_json_choice["value"] = field.to_json(json_choice["value"])
            else:
                new_json_choice = field.to_json(json_choice)
            return new_json_choice

        def get_text(value):
            """Localize a text value that might be None."""
            if value is None:
                return None
            else:
                return self.runtime.service(self, "i18n").ugettext(value)

        # gets the 'default_value' and 'explicitly_set' attrs
        metadata_field_editor_info = self.runtime.get_field_provenance(self, field)
        metadata_field_editor_info["field_name"] = field.name
        metadata_field_editor_info["display_name"] = get_text(field.display_name)
        metadata_field_editor_info["help"] = get_text(field.help)
        metadata_field_editor_info["value"] = field.read_json(self)

        # We support the following editors:
        # 1. A select editor for fields with a list of possible values (includes Booleans).
        # 2. Number editors for integers and floats.
        # 3. A generic string editor for anything else (editing JSON representation of the value).
        editor_type = "Generic"
        values = field.values
        if "values_provider" in field.runtime_options:
            values = field.runtime_options["values_provider"](self)
        if isinstance(values, (tuple, list)) and len(values) > 0:
            editor_type = "Select"
            values = [jsonify_value(field, json_choice) for json_choice in values]
        elif isinstance(field, Integer):
            editor_type = "Integer"
        elif isinstance(field, Float):
            editor_type = "Float"
        elif isinstance(field, List):
            editor_type = "List"
        elif isinstance(field, Dict):
            editor_type = "Dict"
        elif isinstance(field, RelativeTime):
            editor_type = "RelativeTime"
        elif isinstance(field, String) and field.name == "license":
            editor_type = "License"
        metadata_field_editor_info["type"] = editor_type
        metadata_field_editor_info["options"] = [] if values is None else values

        return metadata_field_editor_info

    def _get_editable_metadata_fields(self):
        """
        Returns the metadata fields to be edited in Studio. These are fields with scope `Scope.settings`.

        Can be limited by extending `non_editable_metadata_fields`.
        """
        metadata_fields = {}

        # Only use the fields from this class, not mixins
        fields = getattr(self, "unmixed_class", self.__class__).fields

        for field in fields.values():
            if field in self.non_editable_metadata_fields:
                continue
            if field.scope not in (Scope.settings, Scope.content):
                continue

            metadata_fields[field.name] = self._create_metadata_editor_info(field)

        return metadata_fields

    @property
    def editable_metadata_fields(self):
        """
        Returns the metadata fields to be edited in Studio.
        """
        editable_fields = self._get_editable_metadata_fields()

        settings_service = self.runtime.service(self, "settings")
        if settings_service:
            xb_settings = settings_service.get_settings_bucket(self)
            if not xb_settings.get("licensing_enabled", False) and "license" in editable_fields:
                del editable_fields["license"]

        # Default Timed Transcript a.k.a `sub` has been deprecated and end users shall
        # not be able to modify it.
        editable_fields.pop("sub")

        languages = [{"label": label, "code": lang} for lang, label in settings.ALL_LANGUAGES]
        languages.sort(key=lambda lang_item: lang_item["label"])
        editable_fields["transcripts"]["custom"] = True
        editable_fields["transcripts"]["languages"] = languages
        editable_fields["transcripts"]["type"] = "VideoTranslations"

        # We need to send ajax requests to show transcript status
        # whenever edx_video_id changes on frontend. Thats why we
        # are changing type to `VideoID` so that a specific
        # Backbonjs view can handle it.
        editable_fields["edx_video_id"]["type"] = "VideoID"

        # `public_access` is a boolean field and by default backbonejs code render it as a dropdown with 2 options
        # but in our case we also need to show an input field with dropdown, the input field will show the url to
        # be shared with leaners. This is not possible with default rendering logic in backbonjs code, that is why
        # we are setting a new type and then do a custom rendering in backbonejs code to render the desired UI.
        editable_fields["public_access"]["type"] = "PublicAccess"
        editable_fields["public_access"]["url"] = self.get_public_video_url()

        # construct transcripts info and also find if `en` subs exist
        transcripts_info = self.get_transcripts_info()
        possible_sub_ids = [self.sub, self.youtube_id_1_0] + get_html5_ids(self.html5_sources)
        video_config_service = self.runtime.service(self, "video_config")
        if video_config_service:
            for sub_id in possible_sub_ids:
                try:
                    _, sub_id, _ = video_config_service.get_transcript(
                        self, lang="en", output_format=TranscriptExtensions.TXT
                    )
                    transcripts_info["transcripts"] = dict(transcripts_info["transcripts"], en=sub_id)
                    break
                except TranscriptNotFoundError:
                    continue

        editable_fields["transcripts"]["value"] = transcripts_info["transcripts"]
        editable_fields["transcripts"]["urlRoot"] = self.runtime.handler_url(
            self, "studio_transcript", "translation"
        ).rstrip("/?")
        editable_fields["handout"]["type"] = "FileUploader"

        return editable_fields
