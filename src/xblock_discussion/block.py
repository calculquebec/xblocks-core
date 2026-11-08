"""
Discussion XBlock
"""

import logging
import urllib

import markupsafe
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import get_language_bidi
from web_fragments.fragment import Fragment
from xblock.completable import XBlockCompletionMode
from xblock.core import XBlock
from xblock.fields import UNIQUE_ID, Scope, String
from xblock.utils.resources import ResourceLoader
from xblock.utils.studio_editable import StudioEditableXBlockMixin

from xblocks_core.legacy_utils.xml_utils import LegacyXmlMixin

log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)
Text = markupsafe.escape  # pylint: disable=invalid-name


def _(text):
    """
    A noop underscore function that marks strings for extraction.
    """
    return text


def HTML(html):  # pylint: disable=invalid-name
    """
    Mark a string as already HTML, so that it won't be escaped before output.

    Use this function when formatting HTML into other strings.  It must be
    used in conjunction with ``Text()``, and both ``HTML()`` and ``Text()``
    must be closed before any calls to ``format()``::

        <%page expression_filter="h"/>
        <%!
        from django.utils.translation import gettext as _

        from openedx.core.djangolib.markup import HTML, Text
        %>
        ${Text(_("Write & send {start}email{end}")).format(
            start=HTML("<a href='mailto:{}'>").format(user.email),
            end=HTML("</a>"),
        )}

    """
    return markupsafe.Markup(html)


@XBlock.needs("i18n")
@XBlock.needs("user")
@XBlock.wants("discussion_config_service")
# pylint: disable=abstract-method
class DiscussionXBlock(XBlock, StudioEditableXBlockMixin, LegacyXmlMixin):
    """
    Provides a discussion forum that is inline with other content in the courseware.
    """

    is_extracted = True
    completion_mode = XBlockCompletionMode.EXCLUDED

    discussion_id = String(scope=Scope.settings, default=UNIQUE_ID)
    display_name = String(
        display_name=_("Display Name"),
        help=_("The display name for this component."),
        default="Discussion",
        scope=Scope.settings,
    )
    discussion_category = String(
        display_name=_("Category"),
        default=_("Week 1"),
        help=_(
            "A category name for the discussion. "
            "This name appears in the left pane of the discussion forum for the course."
        ),
        scope=Scope.settings,
    )
    discussion_target = String(
        display_name=_("Subcategory"),
        default="Topic-Level Student-Visible Label",
        help=_(
            "A subcategory name for the discussion. "
            "This name appears in the left pane of the discussion forum for the course."
        ),
        scope=Scope.settings,
    )
    sort_key = String(scope=Scope.settings)

    editable_fields = ["display_name", "discussion_category", "discussion_target"]

    has_author_view = True  # Tells Studio to use author_view

    @property
    def discussion_config(self):
        """
        Returns discussion service.
        """
        return self.runtime.service(self, "discussion_config_service")

    @property
    def is_visible(self):
        """
        Discussion Xblock does not support new OPEN_EDX provider
        """
        return self.discussion_config.is_discussion_visible(self.context_key)

    @property
    def django_user(self):
        """
        Returns django user associated with user currently interacting
        with the XBlock.
        """
        user_service = self.runtime.service(self, "user")
        if not user_service:
            return None
        return user_service._django_user  # pylint: disable=protected-access

    def add_resource_urls(self, fragment):
        """
        Adds URLs for JS and CSS resources that this XBlock depends on to `fragment`.
        """
        css_file_path = "css/inline-discussion-rtl.css" if get_language_bidi() else "css/inline-discussion.css"
        fragment.add_css_url(self.runtime.local_resource_url(self, f"public/{css_file_path}"))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, "public/js/discussion_bundle.js"))

    def has_permission(self, permission):
        """
        Encapsulates lms specific functionality, as `has_permission` is not
        importable outside of lms context, namely in tests.

        :param user:
        :param str permission: Permission
        :rtype: bool
        """
        if self.discussion_config:
            return self.discussion_config.has_permission(self.django_user, permission, self.context_key)
        else:
            return False

    def student_view(self, context=None):
        """
        Renders student view for LMS.
        """

        fragment = Fragment()

        if not self.is_visible:
            return fragment

        self.add_resource_urls(fragment)
        login_msg = ""

        if not self.django_user.is_authenticated:
            qs = urllib.parse.urlencode(
                {
                    "course_id": self.context_key,
                    "enrollment_action": "enroll",
                    "email_opt_in": False,
                }
            )
            login_msg = Text(
                _(
                    "You are not signed in. To view the discussion content, {sign_in_link} or "
                    "{register_link}, and enroll in this course."
                )
            ).format(
                sign_in_link=HTML('<a href="{url}">{sign_in_label}</a>').format(
                    sign_in_label=_("sign in"),
                    url="{}?{}".format(reverse("signin_user"), qs),
                ),
                register_link=HTML('<a href="/{url}">{register_label}</a>').format(
                    register_label=_("register"),
                    url="{}?{}".format(reverse("register_user"), qs),
                ),
            )

        if self.discussion_config.is_discussion_enabled:
            context = {
                "discussion_id": self.discussion_id,
                "display_name": self.display_name if self.display_name else _("Discussion"),
                "user": self.django_user,
                "course_id": self.context_key,
                "discussion_category": self.discussion_category,
                "discussion_target": self.discussion_target,
                "can_create_thread": self.has_permission("create_thread"),
                "can_create_comment": self.has_permission("create_comment"),
                "can_create_subcomment": self.has_permission("create_sub_comment"),
                "login_msg": login_msg,
                "PLATFORM_NAME": settings.PLATFORM_NAME,
                "enable_discussion_home_panel": settings.FEATURES.get("ENABLE_DISCUSSION_HOME_PANEL", False),
            }
            fragment.add_content(render_to_string("discussion_templates/_discussion_inline.html", context))

        fragment.initialize_js("DiscussionInlineBlock")

        return fragment

    def author_view(self, context=None):
        """
        Renders author view for Studio.
        """
        fragment = Fragment()
        context = {
            "discussion_id": self.discussion_id,
            "is_visible": self.is_visible,
        }
        fragment.add_content(loader.render_django_template("templates/_discussion_inline_studio.html", context))
        return fragment

    def student_view_data(self):
        """
        Returns a JSON representation of the student_view of this XBlock.
        """
        return {"topic_id": self.discussion_id}

    @classmethod
    def parse_xml(cls, node, runtime, keys):
        """
        Parses OLX into XBlock.

        This method is overridden here to allow parsing legacy OLX, coming from discussion XModule.
        XBlock stores all the associated data, fields and children in a XML element inlined into vertical XML file
        XModule stored only minimal data on the element included into vertical XML and used a dedicated "discussion"
        folder in OLX to store fields and children. Also, some info was put into "policy.json" file.

        If no external data sources are found (file in "discussion" folder), it is exactly equivalent to base method
        XBlock.parse_xml. Otherwise this method parses file in "discussion" folder (known as definition_xml), applies
        policy.json and updates fields accordingly.
        """
        block = super().parse_xml(node, runtime, keys)

        cls._apply_metadata_and_policy(block, node, runtime)

        return block

    @classmethod
    def _apply_metadata_and_policy(cls, block, node, runtime):
        """
        Attempt to load definition XML from "discussion" folder in OLX, than parse it and update block fields
        """
        if node.get("url_name") is None:
            return  # Newer/XBlock XML format - no need to load an additional file.
        try:
            definition_xml, _ = cls.load_definition_xml(node, runtime, block.scope_ids.def_id)
        except Exception as err:  # pylint: disable=broad-except
            log.info(
                "Exception %s when trying to load definition xml for block %s - assuming XBlock export format",
                err,
                block,
            )
            return

        metadata = cls.load_metadata(definition_xml)
        cls.apply_policy(metadata, runtime.get_policy(block.usage_key))

        for field_name, value in metadata.items():
            if field_name in block.fields:
                setattr(block, field_name, value)
