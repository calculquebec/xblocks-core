"""
Module contains utils specific for video_block but not for transcripts.
"""

import logging
import re
from collections import OrderedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import get_language_info
from requests.exceptions import Timeout

log = logging.getLogger(__name__)


def create_youtube_string(block):
    """
    Create a string of Youtube IDs from `block`'s metadata
    attributes. Only writes a speed if an ID is present in the
    block.  Necessary for backwards compatibility with XML-based
    courses.
    """
    youtube_ids = [block.youtube_id_0_75, block.youtube_id_1_0, block.youtube_id_1_25, block.youtube_id_1_5]
    youtube_speeds = ["0.75", "1.00", "1.25", "1.50"]
    return ",".join([":".join(pair) for pair in zip(youtube_speeds, youtube_ids, strict=False) if pair[1]])


def rewrite_video_url(cdn_base_url, original_video_url):
    """
    Returns a re-written video URL for cases when an alternate source
    has been configured and is selected using factors like
    user location.

    Re-write rules for country codes are specified via the
    EDX_VIDEO_CDN_URLS configuration structure.

    :param cdn_base_url: The scheme, hostname, port and any relevant path prefix
        for the alternate CDN, for example: https://mirror.example.cn/edx
    :param original_video_url: The canonical source for this video,
        for example: https://cdn.example.com/edx-course-videos/VIDEO101/001.mp4
    :return: The re-written URL
    """

    if (not cdn_base_url) or (not original_video_url):
        return None

    parsed = urlparse(original_video_url)
    # Contruction of the rewrite url is intentionally very flexible of input.
    # For example, https://www.edx.org/ + /foo.html will be rewritten to
    # https://www.edx.org/foo.html.
    rewritten_url = cdn_base_url.rstrip("/") + "/" + parsed.path.lstrip("/")
    validator = URLValidator()

    try:
        validator(rewritten_url)
        return rewritten_url
    except ValidationError:
        log.warning("Invalid CDN rewrite URL encountered, %s", rewritten_url)

    # Mimic the behavior of removed get_video_from_cdn in this regard and
    # return None causing the caller to use the original URL.
    return None


def get_poster(video):
    """
    Generate poster metadata.

    youtube_streams is string that contains '1.00:youtube_id'

    Poster metadata is dict of youtube url for image thumbnail and edx logo
    """
    if not video.bumper.get("enabled"):
        return None

    poster = OrderedDict({"url": "", "type": ""})

    if video.youtube_streams:
        youtube_id = video.youtube_streams.split("1.00:")[1].split(",")[0]
        poster["url"] = settings.YOUTUBE["IMAGE_API"].format(youtube_id=youtube_id)
        poster["type"] = "youtube"
    else:
        poster["url"] = "https://www.edx.org/sites/default/files/theme/edx-logo-header.png"
        poster["type"] = "html5"

    return poster


def format_xml_exception_message(location, key, value):
    """
    Generate exception message for VideoBlock class which will use for ValueError and UnicodeDecodeError
    when setting xml attributes.
    """
    exception_message = f"Block-location:{str(location)}, Key:{key}, Value:{value}"
    return exception_message


def set_query_parameter(url, param_name, param_value):
    """
    Given a URL, set or replace a query parameter and return the
    modified URL.
    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def load_metadata_from_youtube(video_id, request):
    """
    Get metadata about a YouTube video.

    This method is used via the standalone /courses/yt_video_metadata REST API
    endpoint, or via the video XBlock as a its 'yt_video_metadata' handler.
    """
    metadata = {}
    status_code = 500
    if video_id and settings.YOUTUBE_API_KEY and settings.YOUTUBE_API_KEY != "PUT_YOUR_API_KEY_HERE":
        yt_api_key = settings.YOUTUBE_API_KEY
        yt_metadata_url = settings.YOUTUBE["METADATA_URL"]
        yt_timeout = settings.YOUTUBE.get("TEST_TIMEOUT", 1500) / 1000  # converting milli seconds to seconds

        headers = {}
        http_referer = None

        try:
            # This raises an attribute error if called from the xblock yt_video_metadata handler, which passes
            # a webob request instead of a django request.
            http_referer = request.META.get("HTTP_REFERER")
        except AttributeError:
            # So here, let's assume it's a webob request and access the referer the webob way.
            http_referer = request.referer

        if http_referer:
            headers["Referer"] = http_referer

        payload = {"id": video_id, "part": "contentDetails", "key": yt_api_key}
        try:
            res = requests.get(yt_metadata_url, params=payload, timeout=yt_timeout, headers=headers)
            status_code = res.status_code
            if res.status_code == 200:
                try:
                    res_json = res.json()
                    if res_json.get("items", []):
                        metadata = res_json
                    else:
                        logging.warning(
                            "Unable to find the items in response. Following response was received: %s", res.text
                        )
                except ValueError:
                    logging.warning("Unable to decode response to json. Following response was received: %s", res.text)
            else:
                logging.warning(
                    "YouTube API request failed with status code=%s - Error message is=%s", status_code, res.text
                )
        except (Timeout, ConnectionError):
            logging.warning("YouTube API request failed because of connection time out or connection error")
    else:
        logging.warning("YouTube API key or video id is None. Please make sure API key and video id is not None")

    return metadata, status_code


def get_resource_url(xblock, path, package_scope=None):
    """
    Return the runtime URL for a static resource in this XBlock's package.

    When the Django pipeline is enabled or REQUIRE_DEBUG is False, uses the
    pipeline path (e.g. {package_scope}/public/{path}). Otherwise uses the
    dev path (e.g. public/{path}). See platform's xblock_local_resource_url() in:
    openedx/core/lib/xblock_utils/__init__.py

    Arguments:
        xblock: The XBlock instance (for runtime.local_resource_url).
        path (str): Relative path within the package, e.g. "css/video.css".
        package_scope (str): Package name prefix, e.g. "video". If None,
            both paths are "public/{path}"; otherwise pipeline adds the prefix.

    Returns:
        str: URL from xblock.runtime.local_resource_url() for the resource.
    """
    pipeline_path = dev_path = f"public/{path}"
    if package_scope:
        pipeline_path = f"{package_scope}/{pipeline_path}"
    pipeline = getattr(settings, "PIPELINE", {})
    if pipeline.get("PIPELINE_ENABLED", True) or not getattr(settings, "REQUIRE_DEBUG", False):
        resource_path = pipeline_path
    else:
        resource_path = dev_path
    return xblock.runtime.local_resource_url(xblock, resource_path)


def get_edxval_api():
    """
    Lazy import for edxval_api to prevent AppRegistryNotReady errors
    during Django startup.
    """
    try:
        import edxval.api as edxval_api  # pylint: disable=import-outside-toplevel

        return edxval_api
    except ImportError:
        return None


_FILENAME_LANG_SUFFIX_RE = re.compile(
    r"[_.-](?P<lang>[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,4})?)\.(?:mp4|webm|ogv|ogg|m4v)$",
    re.IGNORECASE,
)


def resolve_audio_track_label(lang_code, strict=False):
    """
    Resolve a human-readable native label (e.g. 'Français', 'English') for a BCP-47 language code.

    When strict=True, returns None if the language code is not recognized.
    When strict=False, falls back to the uppercase language code.
    """
    if not lang_code:
        return None if strict else ""

    lowercase_code = lang_code.lower()
    language_dict = getattr(settings, "LANGUAGE_DICT", {})
    if local_name := language_dict.get(lowercase_code):
        return local_name[0].upper() + local_name[1:]

    try:
        lang_info = get_language_info(lang_code)
        name_local = lang_info.get("name_local", "")
        if name_local:
            return name_local[0].upper() + name_local[1:]
    except KeyError:
        pass

    for code, language_label in getattr(settings, "ALL_LANGUAGES", []):
        if code.lower() == lowercase_code:
            return language_label

    if strict:
        return None
    return lang_code.upper()


def extract_audio_tracks_from_sources(sources, explicit_audio_tracks=None):
    """
    Clean URL fragments from `sources` and derive `audioTracks` metadata when not explicitly set.

    Supports configuring multi-audio tracks directly via Studio's "Video URL" and "Fallback videos"
    fields (`html5_sources`):
      1. Explicit `#lang=<code>` hash on each video URL:
         - `https://.../video1.mp4#lang=fr`
         - `https://.../video2.mp4#lang=en`
      2. Filename language suffix across 2+ video URLs:
         - `https://.../video_fr.mp4`
         - `https://.../video_en.mp4`
      3. HLS `.m3u8` URLs:
         - Audio tracks are auto-discovered from `#EXT-X-MEDIA:TYPE=AUDIO` by `hls.js` on the client,
           or can be specified via `https://.../master.m3u8#lang=fr,en`.

    Language labels (e.g. 'Français', 'English') are resolved automatically from the language code.

    Returns:
        Tuple of (cleaned_sources, audio_tracks)
    """
    cleaned_sources = []
    hls_fragment_tracks = []
    explicit_fragment_tracks = []
    inferred_suffix_tracks = []

    for raw_url in sources or []:
        if not raw_url:
            continue

        scheme, netloc, path, query, fragment = urlsplit(raw_url)
        clean_url = urlunsplit((scheme, netloc, path, query, ""))
        is_hls = path.lower().endswith(".m3u8")

        fragment_handled = False
        if fragment:
            qs = parse_qs(fragment, keep_blank_values=False)
            if "lang" in qs:
                fragment_handled = True
                lang_param = qs["lang"][0].strip()
                if is_hls and "," in lang_param:
                    for code in lang_param.split(","):
                        code = code.strip()
                        if code:
                            hls_fragment_tracks.append(
                                {"lang": code, "label": resolve_audio_track_label(code)}
                            )
                else:
                    track_entry = {
                        "lang": lang_param,
                        "label": resolve_audio_track_label(lang_param),
                    }
                    if not is_hls:
                        track_entry["src"] = clean_url
                    explicit_fragment_tracks.append(track_entry)

        final_url = clean_url if fragment_handled else raw_url
        cleaned_sources.append(final_url)

        if not fragment_handled and not is_hls:
            filename = path.rsplit("/", 1)[-1]
            match = _FILENAME_LANG_SUFFIX_RE.search(filename)
            if match:
                lang = match.group("lang")
                label = resolve_audio_track_label(lang, strict=True)
                if label:
                    inferred_suffix_tracks.append(
                        {
                            "lang": lang.lower(),
                            "label": label,
                            "src": final_url,
                        }
                    )

    if explicit_audio_tracks:
        return cleaned_sources, explicit_audio_tracks

    if len(hls_fragment_tracks) >= 2:
        return cleaned_sources, hls_fragment_tracks

    distinct_explicit_langs = {t["lang"].lower() for t in explicit_fragment_tracks}
    if len(explicit_fragment_tracks) >= 2 and len(distinct_explicit_langs) >= 2:
        return cleaned_sources, explicit_fragment_tracks

    non_hls_sources = [s for s in cleaned_sources if not s.lower().split("?", 1)[0].endswith(".m3u8")]
    distinct_inferred_langs = {t["lang"].lower() for t in inferred_suffix_tracks}
    if (
        len(inferred_suffix_tracks) >= 2
        and len(inferred_suffix_tracks) == len(non_hls_sources)
        and len(distinct_inferred_langs) >= 2
    ):
        return cleaned_sources, inferred_suffix_tracks

    return cleaned_sources, []

