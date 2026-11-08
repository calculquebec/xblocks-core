"""
Utilities for static content attached to the Video XBlock.

Utilities has been copied from edx-platform/xmodule/contentstore/content.py
"""

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import AssetKey
from opaque_keys.edx.locator import AssetLocator


def compute_location(course_key, path, revision=None, is_thumbnail=False):  # pylint: disable=unused-argument
    """
    Constructs a location object for static content.

    - course_key: the course that this asset belongs to
    - path: is the name of the static asset
    - revision: is the object's revision information
    - is_thumbnail: is whether or not we want the thumbnail version of this asset
    """
    path = path.replace("/", "_")
    return course_key.make_asset_key(
        "asset" if not is_thumbnail else "thumbnail",
        AssetLocator.clean_keeping_underscores(path),
    ).for_branch(None)


def get_location_from_path(path):
    """
    Generate an AssetKey for the given path (old c4x/org/course/asset/name syntax).
    """
    try:
        return AssetKey.from_string(path)
    except InvalidKeyError:
        # TODO - re-address this once LMS-11198 is tackled.
        if path.startswith("/") or path.endswith("/"):
            # try stripping off the leading/trailing slash and try again
            return AssetKey.from_string(path.strip("/"))
        return None


def serialize_asset_key_with_slash(asset_key):
    """
    Legacy code expects the serialized asset key to start with a slash.
    """
    url = str(asset_key)
    if not url.startswith("/"):
        url = "/" + url  # TODO - re-address this once LMS-11198 is tackled.
    return url
