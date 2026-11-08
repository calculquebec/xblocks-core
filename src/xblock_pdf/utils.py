"""Utility functions for PDF XBlock."""

from django.conf import settings


def bool_from_str(str_value):
    """Convert string from submitted form to boolean."""
    return str_value.strip().lower() == "true"


def is_all_download_disabled():
    """Check if all downloads are disabled or not."""
    return getattr(settings, "PDFXBLOCK_DISABLE_ALL_DOWNLOAD", False)
