"""Tests for the PDF Block"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import override_settings
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds
from xblock.test.toy_runtime import ToyRuntime

from xblock_pdf import PDFBlock


def make_block(**fields: str) -> PDFBlock:
    """Build a block with specific fields set."""
    scope_ids = ScopeIds("1", "2", "3", "4")
    return PDFBlock(ToyRuntime(), scope_ids=scope_ids, field_data=DictFieldData(data=fields))


def get_student_content(block: PDFBlock) -> str:
    """Get the contents of a student render for a block."""
    frag = block.student_view()
    as_dict = frag.to_dict()
    return as_dict["content"]


def mock_handle_request(data: dict[str, Any] | None = None, method: str = "POST"):
    """Return a request object compatible with an xblock_handler."""
    mock_request = MagicMock()
    mock_request.method = method
    mock_request.body = json.dumps(data).encode("utf-8")
    return mock_request


def test_defaults_render():
    """Test the basic view loads."""
    block = make_block()
    content = get_student_content(block)
    assert '<iframe src="https://tutorial.math.lamar.edu/pdf/Trig_Cheat_Sheet.pdf"' in content


def test_download_button():
    """Test the allow_download toggle."""
    block = make_block(allow_download=True)
    get_student_content(block)
    content = get_student_content(block)
    assert "Download the PDF" in content
    block.allow_download = False
    content = get_student_content(block)
    assert "Download the PDF" not in content


def test_source_url():
    """Test rendering based on whether or not there's a source URL"""
    block = make_block()
    get_student_content(block)
    content = get_student_content(block)
    assert "Download the Source Document" not in content
    block.source_url = "https://example.com/"
    content = get_student_content(block)
    assert "Download the source document" in content


@override_settings(PDFXBLOCK_DISABLE_ALL_DOWNLOAD=False)
def test_saves_settings():
    """Test that PDF settings are saved."""
    block = make_block()
    request = mock_handle_request(
        {
            "display_name": "Novel application of theory",
            "url": "https://example.com/nature_article.pdf",
            "allow_download": "false",
            "source_text": "Get educated",
            "source_url": "https://example.com/nature_article.tex",
        }
    )
    block.save_pdf(request)
    assert block.display_name == "Novel application of theory"
    assert block.url == "https://example.com/nature_article.pdf"
    assert not block.allow_download
    assert block.source_text == "Get educated"
    assert block.source_url == "https://example.com/nature_article.tex"


@override_settings(PDFXBLOCK_DISABLE_ALL_DOWNLOAD=True)
def test_saves_settings_omits_on_download_disabled_flag():
    """
    Test that fields relating to download are ignored when the universal
    downloads disabled flag is set.
    """
    block = make_block()
    request = mock_handle_request(
        {
            "display_name": "Novel application of theory",
            "url": "https://example.com/nature_article.pdf",
            # These fields shouldn't be visible on the front end,
            # but should be dropped if they somehow are.
            #
            # Potential future improvement would be saving these
            # but ignoring them when rendering. This is not currently
            # the case since the fields are entirely absent from the studio
            # render, and so would send blank data which would error out.
            "allow_download": "false",
            "source_text": "Get educated",
            "source_url": "https://example.com/nature_article.tex",
        }
    )
    block.save_pdf(request)
    assert block.display_name == "Novel application of theory"
    assert block.url == "https://example.com/nature_article.pdf"
    # Flag will be the default, which is True, even though download will be
    # disabled in practice.
    assert block.allow_download
    assert block.source_text == ""
    assert block.source_url == ""


@patch.object(ToyRuntime, "publish")
def test_download_event_fires(mock_publish):
    """Test that we fire a download event."""
    block = make_block()
    request = mock_handle_request()
    block.on_download(request)
    mock_publish.assert_called_with(
        block,
        "edx.pdf.downloaded",
        {
            "url": "https://tutorial.math.lamar.edu/pdf/Trig_Cheat_Sheet.pdf",
            "source_url": "",
        },
    )


def test_get_settings():
    """Test that fetching the block's settings works."""
    block = make_block()
    request = mock_handle_request({}, method="GET")
    result = json.loads(block.load_pdf(request).body)
    assert result["display_name"] == "PDF"
