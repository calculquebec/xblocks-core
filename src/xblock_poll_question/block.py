"""Poll block is ungraded xmodule used by students to
to do set of polls.

On the client side we show:
If student does not yet anwered - Question with set of choices.
If student have answered - Question with statistics for each answers.
"""

import json
import logging
from collections import OrderedDict
from copy import deepcopy

import markupsafe
from django.utils.translation import gettext_noop as _
from lxml import etree
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Dict, List, Scope, String
from xblock.utils.resources import ResourceLoader

from xblocks_core.legacy_utils.xml_utils import LegacyXmlMixin

Text = markupsafe.escape
resource_loader = ResourceLoader(__name__)
log = logging.getLogger(__name__)


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
class PollBlock(LegacyXmlMixin, XBlock):
    """Poll Block"""

    # Indicates that this XBlock has been extracted from edx-platform.
    is_extracted = True

    # Name of poll to use in links to this poll
    display_name = String(
        help=_("The display name for this component."),
        scope=Scope.settings,
        default="poll_question",
    )

    voted = Boolean(help=_("Whether this student has voted on the poll"), scope=Scope.user_state, default=False)
    poll_answer = String(help=_("Student answer"), scope=Scope.user_state, default="")
    poll_answers = Dict(help=_("Poll answers from all students"), scope=Scope.user_state_summary)

    # List of answers, in the form {'id': 'some id', 'text': 'the answer text'}
    answers = List(help=_("Poll answers from xml"), scope=Scope.content, default=[])

    question = String(help=_("Poll question"), scope=Scope.content, default="")

    js_module_name = "poll"

    _tag_name = "poll_question"
    _child_tag_name = "answer"

    def handle_ajax(self, dispatch, data):  # legacy support for tests
        """
        Legacy method to mimic old ajax handler behavior for backward compatibility.
        """
        if dispatch == "get_state":
            return json.dumps(self.handle_get_state(data))
        else:
            return json.dumps(self.submit_answer(dispatch))

    def student_view(self, _context):
        """
        Renders the student view.
        """

        frag = Fragment()
        frag.add_content(
            resource_loader.render_django_template(
                "templates/poll.html",
                {
                    "element_id": self.usage_key.html_id(),
                    "element_class": self.usage_key.block_type,
                    "configuration_json": self.dump_poll(),
                },
                i18n_service=self.runtime.service(self, "i18n"),
            )
        )
        frag.add_css(resource_loader.load_unicode("static/css/poll.css"))
        frag.add_javascript(resource_loader.load_unicode("static/js/src/poll.js"))
        frag.initialize_js("PollBlock")
        return frag

    def dump_poll(self):
        """Dump poll information.

        Returns:
            string - Serialize json.
        """
        # FIXME: hack for resolving caching `default={}` during definition
        # poll_answers field

        if self.poll_answers is None:
            self.poll_answers = {}

        answers_to_json = OrderedDict()

        # # # FIXME: fix this, when xblock support mutable types.
        # # # Now we use this hack.
        temp_poll_answers = self.poll_answers

        # # # Fill self.poll_answers, prepare data for template context.
        for answer in self.answers:
            # Set default count for answer = 0.
            if answer["id"] not in temp_poll_answers:
                temp_poll_answers[answer["id"]] = 0
            answers_to_json[answer["id"]] = answer["text"]
        self.poll_answers = temp_poll_answers

        return json.dumps(
            {
                "answers": answers_to_json,
                "question": self.question,
                "poll_answer": self.poll_answer,
                "poll_answers": self.poll_answers,
                "total": sum(self.poll_answers.values()) if self.voted else 0,
                "reset": str(self.xml_attributes.get("reset", "true")).lower(),
            }
        )

    @XBlock.json_handler
    def handle_get_state(self, data, suffix=""):  # pylint: disable=unused-argument
        return {
            "poll_answer": self.poll_answer,
            "poll_answers": self.poll_answers,
            "total": sum(self.poll_answers.values()),
        }

    def submit_answer(self, answer):
        """
        Submits a poll answer.
        """
        if not answer:
            return {"error": "No answer provided!"}

        if answer in self.poll_answers and not self.voted:
            # FIXME: fix this, when xblock will support mutable types.
            # Now we use this hack.
            temp_poll_answers = self.poll_answers
            temp_poll_answers[answer] += 1
            self.poll_answers = temp_poll_answers

            self.voted = True
            self.poll_answer = answer
            return {
                "poll_answers": self.poll_answers,
                "total": sum(self.poll_answers.values()),
                "callback": {"objectName": "Conditional"},
            }
        return {"error": "Unknown Command!"}

    @XBlock.json_handler
    def handle_submit_state(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        handler to submit poll answer.
        """
        answer = data.get("answer")  # Extract the answer from the data payload
        return self.submit_answer(answer)

    @XBlock.json_handler
    def handle_reset_state(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        handler to Reset poll answer.
        """

        self.voted = False

        # FIXME: fix this, when xblock will support mutable types.
        # Now we use this hack.
        temp_poll_answers = self.poll_answers
        temp_poll_answers[self.poll_answer] -= 1
        self.poll_answers = temp_poll_answers
        self.poll_answer = ""
        return {"status": "success"}

    @staticmethod
    def workbench_scenarios():
        """Create canned scenario for display in the workbench."""
        return [
            (
                "PollBlock",
                """<_poll_question_extracted/>
                """,
            ),
            (
                "Multiple PollBlock",
                """<vertical_demo>
                <_poll_question_extracted/>
                <_poll_question_extracted/>
                <_poll_question_extracted/>
                </vertical_demo>
                """,
            ),
        ]

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        """
        Pull out the data into a dictionary.

        Args:
            xml_object: XML from file.
            system: `system` object.

        Returns:
            tuple: A tuple ``(definition, children)``.

            definition (dict):
                A dictionary containing:

                - ``answers`` (list): List of answers.
                - ``question`` (str): Question string.
        """
        # Check for presense of required tags in xml.
        if len(xml_object.xpath(cls._child_tag_name)) == 0:
            raise ValueError(
                "Poll_question definition must include \
                at least one 'answer' tag"
            )

        xml_object_copy = deepcopy(xml_object)
        answers = []
        for element_answer in xml_object_copy.findall(cls._child_tag_name):
            answer_id = element_answer.get("id", None)
            if answer_id:
                answers.append({"id": answer_id, "text": stringify_children(element_answer)})
            xml_object_copy.remove(element_answer)

        definition = {"answers": answers, "question": stringify_children(xml_object_copy)}
        children = []
        return (definition, children)

    def definition_to_xml(self, resource_fs=None):
        """Return an xml element representing to this definition."""

        poll_str = HTML("<{tag_name}>{text}</{tag_name}>").format(tag_name=self._tag_name, text=self.question)
        xml_object = etree.fromstring(poll_str)
        xml_object.set("display_name", self.display_name)

        def add_child(xml_obj, answer):  # pylint: disable=unused-argument
            # Escape answer text before adding to xml tree.
            answer_text = str(answer["text"])
            child_str = Text("{tag_begin}{text}{tag_end}").format(
                tag_begin=HTML('<{tag_name} id="{id}">').format(tag_name=self._child_tag_name, id=answer["id"]),
                text=answer_text,
                tag_end=HTML("</{tag_name}>").format(tag_name=self._child_tag_name),
            )
            child_node = etree.fromstring(child_str)
            xml_object.append(child_node)

        for answer in self.answers:
            add_child(xml_object, answer)

        return xml_object
