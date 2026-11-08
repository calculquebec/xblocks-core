"""
Utility functions for video block transcripts.
++++++++++++++++++++++++++++++++++++++++++++++
"""

import copy
import logging

from django.conf import settings
from django.utils.translation import get_language_info

from .bumper_utils import get_bumper_settings
from .exceptions import TranscriptNotFoundError
from .video_utils import get_edxval_api

log = logging.getLogger(__name__)

NON_EXISTENT_TRANSCRIPT = "non_existent_dummy_file_name"


class TranscriptExtensions:
    """
    Video block transcript extensions.
    """

    SRT = "srt"
    TXT = "txt"
    SJSON = "sjson"
    mime_types = {
        SRT: "application/x-subrip; charset=utf-8",
        TXT: "text/plain; charset=utf-8",
        SJSON: "application/json",
    }


def get_html5_ids(html5_sources):
    """
    Helper method to parse out an HTML5 source into the ideas
    NOTE: This assumes that '/' are not in the filename
    """
    html5_ids = [x.split("/")[-1].rsplit(".", 1)[0] for x in html5_sources]
    return html5_ids


def subs_filename(subs_id, lang="en"):
    """
    Generate proper filename for storage.
    """
    if lang == "en":
        return f"subs_{subs_id}.srt.sjson"
    else:
        return f"{lang}_subs_{subs_id}.srt.sjson"


def clean_video_id(edx_video_id):
    """
    Cleans an edx video ID.

    Arguments:
        edx_video_id(unicode): edx-val's video identifier
    """
    return edx_video_id and edx_video_id.strip()


def get_available_transcript_languages(edx_video_id):
    """
    Gets available transcript languages for a video.

    Arguments:
        edx_video_id(unicode): edx-val's video identifier

    Returns:
        A list containing distinct transcript language codes against all the passed video ids.
    """
    available_languages = []
    edx_video_id = clean_video_id(edx_video_id)
    edxval_api = get_edxval_api()
    if edxval_api and edx_video_id:
        available_languages = edxval_api.get_available_transcript_languages(video_id=edx_video_id)

    return available_languages


class VideoTranscriptsMixin:
    """Mixin class for transcript functionality.

    This is necessary for VideoBlock.
    """

    def get_default_transcript_language(self, transcripts, dest_lang=None):
        """
        Returns the default transcript language for this video block.

        Args:
            transcripts (dict): A dict with all transcripts and a sub.
            dest_lang (unicode): language coming from unit translation language selector.
        """
        sub, other_lang = transcripts["sub"], transcripts["transcripts"]

        if dest_lang:
            resolved_transcript_dest_lang = resolve_language_code_to_transcript_code(transcripts, dest_lang)
            if resolved_transcript_dest_lang:
                return resolved_transcript_dest_lang
            # language in plugin selector is english and empty transcripts or transcripts and sub exists
            if dest_lang == "en" and (not other_lang or (other_lang and sub)):
                return "en"

        if self.transcript_language in other_lang:
            return self.transcript_language

        if sub:
            return "en"

        if len(other_lang) > 0:
            return sorted(other_lang)[0]

        return "en"

    def get_transcripts_info(self, is_bumper=False):
        """
        Returns a transcript dictionary for the video.

        Arguments:
            is_bumper(bool): If True, the request is for the bumper transcripts
            include_val_transcripts(bool): If True, include edx-val transcripts as well
        """
        # TODO: This causes a circular import when imported at the top-level.
        #       This import will be removed as part of the VideoBlock extraction.
        #       https://github.com/openedx/edx-platform/issues/36282

        if is_bumper:
            transcripts = copy.deepcopy(get_bumper_settings(self).get("transcripts", {}))
            sub = transcripts.pop("en", "")
        else:
            transcripts = self.transcripts if self.transcripts else {}
            sub = self.sub

        # Only attach transcripts that are not empty.
        transcripts = {
            language_code: transcript_file
            for language_code, transcript_file in transcripts.items()
            if transcript_file != ""
        }

        # bumper transcripts are stored in content store so we don't need to include val transcripts
        if not is_bumper:
            transcript_languages = get_available_transcript_languages(edx_video_id=self.edx_video_id)
            # HACK Warning! this is temporary and will be removed once edx-val take over the
            # transcript module and contentstore will only function as fallback until all the
            # data is migrated to edx-val.
            for language_code in transcript_languages:
                if language_code == "en" and not sub:
                    sub = NON_EXISTENT_TRANSCRIPT
                elif not transcripts.get(language_code):
                    transcripts[language_code] = NON_EXISTENT_TRANSCRIPT

        return {
            "sub": sub,
            "transcripts": transcripts,
        }


def resolve_language_code_to_transcript_code(transcripts, dest_lang):
    """
    Attempts to match the requested dest lang with the existing transcript languages
    """
    _, other_lang = transcripts["sub"], transcripts["transcripts"]
    # lang code exists in list of other transcript languages as-is
    if dest_lang in other_lang:
        return dest_lang

    # Language codes can be base languages, 2-3 characters, or they can include a
    # locale (`fr` for french, `fr-ca` for canadian french). Sometimes the part after the
    # dash is capitalized, sometimes it is not. Check both variants.
    dash_index = dest_lang.find("-")
    if dash_index >= 0:
        lowercase_dest_lang = dest_lang.lower()
        if lowercase_dest_lang in other_lang:
            log.debug("language code %s resolved to %s", dest_lang, lowercase_dest_lang)
            return lowercase_dest_lang

        generic_lang_code = lowercase_dest_lang[:dash_index]
        uppercase_dest_lang = generic_lang_code + lowercase_dest_lang[dash_index:].upper()
        if uppercase_dest_lang in other_lang:
            log.debug("language code %s resolved to %s", dest_lang, uppercase_dest_lang)
            return uppercase_dest_lang

        if generic_lang_code in other_lang:
            log.debug("language code %s resolved to generic %s", dest_lang, generic_lang_code)
            return generic_lang_code

    return None


def get_endonym_or_label(language_code):
    """
    Given a language code, attempt to look up the endonym, or local name, for that language
    """

    lowercase_code = language_code.lower()
    # LANGUAGE_DICT is an edx-configured mapping of language codes to endonym. It's a bit more
    # specific than the django utility, so try that first. All language codes in this dict will
    # be lowercase
    if local_name := settings.LANGUAGE_DICT.get(lowercase_code):
        return local_name

    # get_language_info attempts to look up language info in a hardcoded list in
    # django.conf.translations. It will do automatic "generalizations", i.e. it doesn't
    # have `es-419` so it then tries `es`. That's why we only do this after checking
    # LANGUAGE_DICT
    try:
        lang_info = get_language_info(language_code)
        return lang_info["name_local"]
    except KeyError:
        pass

    # Last place to look is in settings.ALL_LANGUAGES. Ideally we find the actual code,
    # but also, check the 'generic' language. If even the generic language isn't found,
    # something is wrong, so log an error and throw an exception.
    first_dash_index = language_code.find("-")
    generic_code = None if first_dash_index == -1 else language_code[:first_dash_index]
    potential_generic_label = None
    for code, language_label in settings.ALL_LANGUAGES:
        # check for lowercase of the whole code, but as far as I can tell, the generic codes are
        # always lowercase
        if code in (language_code, lowercase_code):
            return language_label
        if generic_code and code == generic_code:
            potential_generic_label = language_label
        elif code > language_code:
            break
    if potential_generic_label:
        return potential_generic_label

    log.error("A label was requested for language code `%s` but the code is completely unknown", language_code)
    raise TranscriptNotFoundError(f"Unknown language `{language_code}`")
