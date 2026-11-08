"""
HTML XBlock module for displaying raw HTML content.
This XBlock allows users to embed HTML content inside courses.
"""

import copy
import logging
import os
import re
import sys
import uuid
from html.parser import HTMLParser

from django.conf import settings
from django.utils.translation import gettext_noop as _
from fs.errors import ResourceNotFound
from lxml import etree
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import LibraryLocatorV2
from path import Path as path
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Scope, String
from xblock.utils.resources import ResourceLoader

from xblocks_core.legacy_utils.xml_utils import LegacyXmlMixin, name_to_pathname

log = logging.getLogger(__name__)
resource_loader = ResourceLoader(__name__)

# The global (course-agnostic) anonymous user ID for the user.
ATTR_KEY_DEPRECATED_ANONYMOUS_USER_ID = "edx-platform.deprecated_anonymous_user_id"


class MLStripper(HTMLParser):
    "helper function for html_to_text below"

    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        for attr in attrs:
            if len(attr) >= 2 and attr[0] == "alt":
                self.fed.append(attr[1])

    def handle_data(self, data):
        """takes the data in separate chunks"""
        self.fed.append(data)

    def handle_entityref(self, name):
        """appends the reference to the body"""
        self.fed.append(f"&{name};")

    def get_data(self):
        """joins together the seperate chunks into one cohesive string"""
        return "".join(self.fed)


def html_to_text(html):
    """Convert HTML to plain text."""
    htmlstripper = MLStripper()
    htmlstripper.feed(html)
    return htmlstripper.get_data()


def escape_html_characters(content):
    """
    Remove HTML characters that shouldn't be indexed using ElasticSearch indexer
    This method is complementary to html_to_text method found in xmodule/annotator_mixin.py

    Args:
        content (str): variable to escape html characters from

    Returns:
        content (str): content ready to be index by ElasticSearch

    """

    # Removing HTML comments
    return re.sub(
        r"<!--.*-->",
        "",
        # Removing HTML CDATA
        re.sub(
            r"<!\[CDATA\[.*\]\]>",
            "",
            # Removing HTML-encoded non-breaking space characters
            re.sub(r"(\s|&nbsp;|//)+", " ", html_to_text(content)),
        ),
    )


def check_html(html):
    """
    Check whether the passed in html string can be parsed by lxml.
    Return bool success.
    """
    parser = etree.HTMLParser()
    try:
        etree.fromstring(html, parser)
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return False


def stringify_children(node):
    """
    Return all contents of an xml tree, without the outside tags.
    e.g. if node is parse of

        "<html a="b" foo="bar">Hi <div>there <span>Bruce</span><b>!</b></div><html>"

    should return

        "Hi <div>there <span>Bruce</span><b>!</b></div>"

    fixed from
    http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
    """
    # Useful things to know:

    # node.tostring() -- generates xml for the node, including start
    #                 and end tags.  We'll use this for the children.
    # node.text -- the text after the end of a start tag to the start
    #                 of the first child
    # node.tail -- the text after the end this tag to the start of the
    #                 next element.
    parts = [node.text]
    for c in node.getchildren():
        parts.append(etree.tostring(c, with_tail=True, encoding="unicode"))

    # filter removes possible Nones in texts and tails
    return "".join([part for part in parts if part])


@XBlock.needs("i18n")
# We 'want' the user service, but we don't strictly 'need' it.
# This makes our block more resilient. It won't crash in test environments
# where the user service might not be available.
@XBlock.wants("user")
class HtmlBlockMixin(LegacyXmlMixin, XBlock):
    """
    The HTML XBlock mixin.
    This provides the base class for all Html-ish blocks (including the HTML XBlock).
    """

    display_name = String(
        display_name=_("Display Name"),
        help=_("The display name for this component."),
        scope=Scope.settings,
        # it'd be nice to have a useful default but it screws up other things; so,
        # use display_name_with_default for those
        default=_("Text"),
    )
    data = String(help=_("Html contents to display for this block"), default="", scope=Scope.content)
    upstream_data = String(
        help=_("Upstream html contents to store upstream data field"),
        default=None,
        hidden=True,
        enforce_type=True,
        scope=Scope.content,
    )
    source_code = String(
        help=_("Source code for LaTeX documents. This feature is not well-supported."), scope=Scope.settings
    )
    use_latex_compiler = Boolean(help=_("Enable LaTeX templates?"), default=False, scope=Scope.settings)
    editor = String(
        help=_(
            "Select Visual to enter content and have the editor automatically create the HTML. Select Raw to edit "
            "HTML directly. If you change this setting, you must save the component and then re-open it for editing."
        ),
        display_name=_("Editor"),
        default="visual",
        values=[{"display_name": _("Visual"), "value": "visual"}, {"display_name": _("Raw"), "value": "raw"}],
        scope=Scope.settings,
    )

    ENABLE_HTML_XBLOCK_STUDENT_VIEW_DATA = "ENABLE_HTML_XBLOCK_STUDENT_VIEW_DATA"

    uses_xmodule_styles_setup = True
    template_dir_name = "html"
    show_in_read_only_mode = True

    @XBlock.supports("multi_device")
    def student_view(self, _context):
        """Return a fragment that contains the html for the student view."""
        frag = Fragment(self.get_html())
        frag.add_css(resource_loader.load_unicode("static/css/html.css"))
        frag.add_javascript("""
function HtmlBlock(runtime, element) {
    if (typeof MathJax !== "undefined" && MathJax !== null &&
        MathJax.startup && MathJax.startup.promise) {
        MathJax.startup.promise.then(function() {
            MathJax.typesetPromise([element]);
        });
    }
}
""")
        frag.initialize_js("HtmlBlock")
        return frag

    @XBlock.supports("multi_device")
    def public_view(self, context):
        """Returns a fragment that contains the html for the preview view."""
        return self.student_view(context)

    def student_view_data(self, context=None):  # pylint: disable=unused-argument
        """Return a JSON representation of the student_view of this XBlock."""
        if getattr(settings, "FEATURES", {}).get(self.ENABLE_HTML_XBLOCK_STUDENT_VIEW_DATA, False):
            return {"enabled": True, "html": self.get_html()}
        else:
            return {
                "enabled": False,
                "message": f'To enable, set FEATURES["{self.ENABLE_HTML_XBLOCK_STUDENT_VIEW_DATA}"]',
            }

    def get_html(self):
        """Returns html required for rendering the block."""
        if not self.data:
            return self.data

        data = self.data

        # This code is now more defensive.
        # We check if the user service and the user object exist before using them.
        # This prevents crashes if they are not available.
        user_service = self.runtime.service(self, "user")
        if user_service:
            current_user = user_service.get_current_user()
            if current_user:
                user_id = current_user.opt_attrs.get(ATTR_KEY_DEPRECATED_ANONYMOUS_USER_ID)
                if user_id:
                    data = data.replace("%%USER_ID%%", user_id)
                if current_user.emails:
                    email = current_user.emails[0]
                    data = data.replace("%%USER_EMAIL%%", email)

        # The course ID replacement is always safe to run.
        data = data.replace("%%COURSE_ID%%", str(self.context_key))
        return data

    def studio_view(self, context=None):
        """Return a fragment that contains the html for the studio view."""
        # Only the ReactJS editor is supported for this block.
        # See https://github.com/openedx/frontend-app-authoring/tree/master/src/editors/containers/TextEditor
        raise NotImplementedError

    @classmethod
    def get_customizable_fields(cls) -> dict[str, str | None]:
        return {
            "display_name": "upstream_display_name",
            "data": "upstream_data",
        }

    # VS[compat] TODO (cpennington): Delete this method once all fall 2012 course
    # are being edited in the cms
    @classmethod
    def backcompat_paths(cls, filepath):
        """
        Get paths for html and xml files.
        """
        if filepath.endswith(".html.xml"):
            filepath = filepath[:-9] + ".html"  # backcompat--look for html instead of xml
        if filepath.endswith(".html.html"):
            filepath = filepath[:-5]  # some people like to include .html in filenames..
        candidates = []
        while os.sep in filepath:
            candidates.append(filepath)
            _, _, filepath = filepath.partition(os.sep)

        # also look for .html versions instead of .xml
        new_candidates = []
        for candidate in candidates:
            if candidate.endswith(".xml"):
                new_candidates.append(candidate[:-4] + ".html")
        return candidates + new_candidates

    @classmethod
    def filter_templates(cls, template, course):
        """
        Filter template that contains 'latex' from templates.

        Show them only if use_latex_compiler is set to True in
        course settings.
        """
        return "latex" not in template["template_id"] or course.use_latex_compiler

    def get_context(self):
        """
        an override to add in specific rendering context, in this case we need to
        add in a base path to our c4x content addressing scheme
        """
        # Add some specific HTML rendering context when editing HTML blocks where we pass
        # the root /c4x/ url for assets. This allows client-side substitutions to occur.
        return {
            "module": self,
            "editable_metadata_fields": self.editable_metadata_fields,
            "data": self.data,
            "base_asset_url": self.get_base_url_path_for_course_assets(self.context_key),
            "enable_latex_compiler": self.use_latex_compiler,
            "editor": self.editor,
        }

    def index_dictionary(self):
        xblock_body = super().index_dictionary()
        # Removing script and style
        html_content = re.sub(
            re.compile(
                r"""
                    <script>.*?</script> |
                    <style>.*?</style>
                """,
                re.DOTALL | re.VERBOSE,
            ),
            "",
            self.data,
        )
        html_content = escape_html_characters(html_content)
        html_body = {
            "html_content": html_content,
            "display_name": self.display_name,
        }
        if "content" in xblock_body:
            xblock_body["content"].update(html_body)
        else:
            xblock_body["content"] = html_body
        xblock_body["content_type"] = "Text"
        return xblock_body

    @staticmethod
    def serialize_asset_key_with_slash(asset_key):
        """
        Legacy code expects the serialized asset key to start w/ a slash; so, do that in one place
        :param asset_key:
        """
        url = str(asset_key)
        if not url.startswith("/"):
            url = "/" + url  # TODO - re-address this once LMS-11198 is tackled.
        return url

    @staticmethod
    def get_base_url_path_for_course_assets(course_key):  # pylint: disable=missing-function-docstring
        if (course_key is None) or isinstance(course_key, LibraryLocatorV2):
            return None

        assert isinstance(course_key, CourseKey)
        placeholder_id = uuid.uuid4().hex
        # create a dummy asset location with a fake but unique name. strip off the name, and return it
        url_path = HtmlBlock.serialize_asset_key_with_slash(
            course_key.make_asset_key("asset", placeholder_id).for_branch(None)
        )
        return url_path.replace(placeholder_id, "")

    def save(self):
        """Save block data."""
        if hasattr(self, "children"):
            self.children = [str(c) for c in self.children]
        super().save()

    @staticmethod
    def workbench_scenarios():
        """Create canned scenario for display in the workbench."""
        return [
            ("HtmlBlock", """<_html_extracted/>"""),
            (
                "Multiple HtmlBlock",
                """<vertical_demo><_html_extracted/><_html_extracted/><_html_extracted/></vertical_demo>""",
            ),
        ]

    # NOTE: html descriptors are special.  We do not want to parse and
    # export them ourselves, because that can break things (e.g. lxml
    # adds body tags when it exports, but they should just be html
    # snippets that will be included in the middle of pages.

    @classmethod
    def load_definition(cls, xml_object, system, def_id, id_generator):
        """Load a descriptor from the specified xml_object:

        If there is a filename attribute, load it as a string, and
        log a warning if it is not parseable by etree.HTMLParser.

        If there is not a filename attribute, the definition is the body
        of the xml_object, without the root tag (do not want <html> in the
        middle of a page)

        Args:
            xml_object: an lxml.etree._Element containing the definition to load
            system: the modulestore system or runtime which caches data
            location: the usage id for the block--used to compute the filename if none in the xml_object
            id_generator: used by other impls of this method to generate the usage_id
        """
        filename = xml_object.get("filename")
        if filename is None:
            definition_xml = copy.deepcopy(xml_object)
            cls.clean_metadata_from_xml(definition_xml)
            return {"data": stringify_children(definition_xml)}, []
        else:
            # html is special.  cls.filename_extension is 'xml', but
            # if 'filename' is in the definition, that means to load
            # from .html
            # 'filename' in html pointers is a relative path
            # (not same as 'html/blah.html' when the pointer is in a directory itself)
            pointer_path = "{category}/{url_path}".format(category="html", url_path=name_to_pathname(def_id.block_id))
            base = path(pointer_path).dirname()
            # log.debug("base = {0}, base.dirname={1}, filename={2}".format(base, base.dirname(), filename))
            filepath = f"{base}/{filename}.html"
            # log.debug("looking for html file for {0} at {1}".format(location, filepath))

            # VS[compat]
            # TODO (cpennington): If the file doesn't exist at the right path,
            # give the class a chance to fix it up. The file will be written out
            # again in the correct format.  This should go away once the CMS is
            # online and has imported all current (fall 2012) courses from xml
            if not system.resources_fs.exists(filepath):
                candidates = cls.backcompat_paths(filepath)
                # log.debug("candidates = {0}".format(candidates))
                for candidate in candidates:
                    if system.resources_fs.exists(candidate):
                        filepath = candidate
                        break
            try:
                with system.resources_fs.open(filepath, encoding="utf-8") as infile:
                    html = infile.read()
                    # Log a warning if we can't parse the file, but don't error
                    if len(html) > 0 and not check_html(html):
                        msg = f"Couldn't parse html in {filepath}"
                        log.warning(msg)
                        system.error_tracker("Warning: " + msg)

                    definition = {"data": html}

                    # TODO (ichuang): remove this after migration
                    # for Fall 2012 LMS migration: keep filename (and unmangled filename)
                    definition["filename"] = [filepath, filename]

                    return definition, []

            except ResourceNotFound as err:
                msg = f"Unable to load file contents at path {filepath}: {err} "
                # add more info and re-raise
                raise Exception(msg).with_traceback(sys.exc_info()[2]) from None

    @classmethod
    def parse_xml_new_runtime(cls, node, runtime, keys):
        """
        Parse XML in the new learning-core-based runtime. Since it doesn't yet
        support loading separate .html files, the HTML data is assumed to be in
        a CDATA child or otherwise just inline in the OLX.
        """
        block = runtime.construct_xblock_from_class(cls, keys)
        block.data = stringify_children(node)
        # Attributes become fields.
        for name, value in node.items():
            cls._set_field_if_present(block, name, value, {})
        return block

    def definition_to_xml(self, resource_fs):
        """
        Returns an lxml Element representing the definition of this block.
        This version creates a self-contained definition file that includes
        all necessary metadata for a successful re-import.
        """

        # Write html to file, return an empty tag
        pathname = name_to_pathname(self.usage_key.block_id)
        filepath = f"{self.usage_key.block_type}/{pathname}.html"

        resource_fs.makedirs(os.path.dirname(filepath), recreate=True)
        with resource_fs.open(filepath, "wb") as filestream:
            html_data = self.data.encode("utf-8")
            filestream.write(html_data)

        # write out the relative name
        relname = path(pathname).basename()

        elt = etree.Element("html")
        elt.set("filename", relname)
        return elt

    @property
    def non_editable_metadata_fields(self):
        """`use_latex_compiler` should not be editable in the Studio settings editor."""
        return super().non_editable_metadata_fields + [HtmlBlock.xml_attributes, HtmlBlock.use_latex_compiler]


class HtmlBlock(HtmlBlockMixin):  # pylint: disable=abstract-method
    """
    The HTML XBlock.
    """

    # Indicates that this XBlock has been extracted from edx-platform.
    is_extracted = True
