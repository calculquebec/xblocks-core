"""Mixin that provides AJAX handling for Video XBlock"""

from webob import Response
from webob.multidict import MultiDict
from xblock.core import XBlock


class AjaxHandlerMixin:
    """
    Mixin that provides AJAX handling for Video XBlock
    """

    @property
    def ajax_url(self):
        """
        Returns the URL for the ajax handler.
        """
        return self.runtime.handler_url(self, "ajax_handler", "", "").rstrip("/?")

    @XBlock.handler
    def ajax_handler(self, request, suffix=None):
        """
        XBlock handler that wraps `ajax_handler`
        """

        class FileObjForWebobFiles:
            """
            Turn Webob cgi.FieldStorage uploaded files into pure file objects.

            Webob represents uploaded files as cgi.FieldStorage objects, which
            have a .file attribute.  We wrap the FieldStorage object, delegating
            attribute access to the .file attribute.  But the files have no
            name, so we carry the FieldStorage .filename attribute as the .name.

            """

            def __init__(self, webob_file):
                self.file = webob_file.file
                self.name = webob_file.filename

            def __getattr__(self, name):
                return getattr(self.file, name)

        # WebOb requests have multiple entries for uploaded files.  handle_ajax
        # expects a single entry as a list.
        request_post = MultiDict(request.POST)
        for key in set(request.POST.keys()):
            if hasattr(request.POST[key], "file"):
                request_post[key] = list(map(FileObjForWebobFiles, request.POST.getall(key)))

        response_data = self.handle_ajax(suffix, request_post)
        return Response(response_data, content_type="application/json", charset="UTF-8")
