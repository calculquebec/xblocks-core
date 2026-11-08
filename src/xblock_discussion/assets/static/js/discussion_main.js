/*
    Webpack entry: imports all discussion JS in dependency order.
 */

// Vendor
import './vendor/Markdown.Converter.js';
import './vendor/Markdown.Sanitizer.js';
import './vendor/Markdown.Editor.js';
import './vendor/jquery.ajaxfileupload.js';
import './vendor/jquery.timeago.js';
import './vendor/jquery.timeago.locale.js';
import './vendor/jquery.truncate.js';
import './vendor/split.js';
// MathJax
import './mathjax_accessible.js';
import './mathjax_delay_renderer.js';
// Core
import './common/utils.js';
import './common/models/discussion_course_settings.js';
import './common/models/discussion_user.js';
import './common/content.js';
import './common/discussion.js';
import './common/mathjax_include.js';
import './customwmd.js';
// Views
import './common/views/discussion_content_view.js';
import './common/views/discussion_inline_view.js';
import './common/views/discussion_thread_edit_view.js';
import './common/views/discussion_thread_list_view.js';
import './common/views/discussion_thread_profile_view.js';
import './common/views/discussion_thread_show_view.js';
import './common/views/discussion_thread_view.js';
import './common/views/discussion_topic_menu_view.js';
import './common/views/new_post_view.js';
import './common/views/response_comment_edit_view.js';
import './common/views/response_comment_show_view.js';
import './common/views/response_comment_view.js';
import './common/views/thread_response_edit_view.js';
import './common/views/thread_response_show_view.js';
import './common/views/thread_response_view.js';
