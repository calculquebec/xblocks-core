"""
Module contains utils specific for video_block but not for transcripts.
"""

import logging
from collections import OrderedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
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
