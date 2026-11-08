"""pdfXBlock main Python class."""

import json

from django.utils.translation import gettext_noop as _
from web_fragments.fragment import Fragment
from webob import Response
from xblock.core import XBlock
from xblock.fields import Boolean, Scope, String
from xblock.utils.resources import ResourceLoader

from .utils import bool_from_str, is_all_download_disabled

resource_loader = ResourceLoader(__name__)


@XBlock.needs("i18n")
class PDFBlock(XBlock):
    """PDF XBlock. Allows authors to embed PDFs in their courses."""

    icon_class = "other"

    display_name = String(
        display_name=_("Display Name"),
        default=_("PDF"),
        scope=Scope.settings,
        help=_("This name appears in the horizontal navigation at the top of the page."),
    )

    url = String(
        display_name=_("PDF URL"),
        default=_("https://tutorial.math.lamar.edu/pdf/Trig_Cheat_Sheet.pdf"),
        scope=Scope.content,
        help=_("The URL for your PDF."),
    )

    allow_download = Boolean(
        display_name=_("PDF Download Allowed"),
        default=True,
        scope=Scope.content,
        help=_("Display a download button for this PDF."),
    )

    source_text = String(
        display_name=_("Source document button text"),
        default="",
        scope=Scope.content,
        help=_(
            "Add a download link for the source file of your PDF. "
            "Use it for example to provide the PowerPoint file used to create this PDF."
        ),
    )

    source_url = String(
        display_name=_("Source document URL"),
        default="",
        scope=Scope.content,
        help=_(
            "Add a download link for the source file of your PDF. "
            "Use it for example to provide the PowerPoint file used to create this PDF."
        ),
    )

    @property
    def raw_settings(self):
        """Get the raw settings of the XBlock as a dictionary."""
        return {
            "display_name": self.display_name,
            "url": self.url,
            "allow_download": self.allow_download,
            "disable_all_download": is_all_download_disabled(),
            "source_text": self.source_text,
            "source_url": self.source_url,
        }

    def student_view(self, context=None):  # pylint: disable=unused-argument
        """Primary view of the XBlock, shown to students when viewing courses."""
        html = resource_loader.render_django_template(
            "templates/html/pdf.html",
            context=self.raw_settings,
            i18n_service=self.runtime.service(self, "i18n"),
        )

        event_type = "edx.pdf.loaded"
        event_data = {
            "url": self.url,
            "source_url": self.source_url,
        }
        self.runtime.publish(self, event_type, event_data)
        frag = Fragment(html)
        frag.add_javascript(resource_loader.load_unicode("static/js/pdf.js"))
        frag.initialize_js("pdfXBlockInitView")
        return frag

    def studio_view(self, context=None):
        """Return a fragment that contains the html for the studio view."""
        # Only the ReactJS editor is supported for this block.
        # See https://github.com/openedx/frontend-app-authoring/tree/master/src/editors/containers/PdfEditor
        raise NotImplementedError  # pragma: no cover

    @XBlock.json_handler
    def on_download(self, data, suffix=""):  # pylint: disable=unused-argument
        """Download file event handler."""
        event_type = "edx.pdf.downloaded"
        event_data = {
            "url": self.url,
            "source_url": self.source_url,
        }
        self.runtime.publish(self, event_type, event_data)

    @XBlock.handler
    def load_pdf(self, *_args, **_kwargs):
        """Get the PDF block's settings in JSON format."""
        return Response(json.dumps(self.raw_settings), content_type="application/json", charset="utf8")

    @XBlock.json_handler
    def save_pdf(self, data, suffix=""):  # pylint: disable=unused-argument
        """Save handler."""
        self.display_name = data["display_name"]
        self.url = data["url"]

        if not is_all_download_disabled():
            self.allow_download = bool_from_str(data["allow_download"])
            self.source_text = data["source_text"]
            self.source_url = data["source_url"]

        return {
            "result": "success",
        }
