
import './js/src/utils/ajax_prefix.js';
import './js/src/utils/add_ajax_prefix.js';
import './js/src/10_main.js';
import '../tests/spec_helpers/vertical_student_view.js';
import '../tests/spec_helpers/jasmine-extensions.js';
import '../tests/spec_helpers/jasmine-waituntil.js';
import '../tests/spec_helpers/helper.js';
import '../tests/spec_helpers/video_helper.js';

// These are the tests that will be run
import '../tests/js/async_process_spec.js';
import '../tests/js/completion_spec.js';
import '../tests/js/events_spec.js';
import '../tests/js/general_spec.js';
import '../tests/js/initialize_spec.js';
import '../tests/js/iterator_spec.js';
import '../tests/js/resizer_spec.js';
import '../tests/js/sjson_spec.js';
import '../tests/js/social_share_spec.js';
import '../tests/js/video_context_menu_spec.js';
import '../tests/js/video_focus_grabber_spec.js';
import '../tests/js/video_full_screen_spec.js';
import '../tests/js/video_play_pause_control_spec.js';
import '../tests/js/video_play_placeholder_spec.js';
import '../tests/js/video_play_skip_control_spec.js';
import '../tests/js/video_quality_control_spec.js';
import '../tests/js/video_save_state_plugin_spec.js';
import '../tests/js/video_skip_control_spec.js';
import '../tests/js/video_storage_spec.js';
import '../tests/js/video_transcript_feedback_spec.js';
import '../tests/js/video_volume_control_spec.js';
import '../tests/js/video_autoadvance_spec.js';
import '../tests/js/video_events_plugin_spec.js';
import '../tests/js/video_control_spec.js';
import '../tests/js/video_caption_spec.js';
import '../tests/js/video_speed_control_spec.js';
import '../tests/js/video_events_bumper_plugin_spec.js';

import '../tests/js/video_poster_spec.js';
import '../tests/js/video_progress_slider_spec.js';
import '../tests/js/video_bumper_spec.js';
import '../tests/js/html5_video_spec.js';
import '../tests/js/video_player_spec.js';
import '../tests/js/time_spec.js';

import HtmlUtils from 'edx-ui-toolkit/js/utils/html-utils';
import StringUtils from 'edx-ui-toolkit/js/utils/string-utils';

window._ = _;
window.edx = window.edx || {};
window.edx.HtmlUtils = HtmlUtils;
window.edx.StringUtils = StringUtils;
