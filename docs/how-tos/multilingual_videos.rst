Configuring Multilingual Videos
===============================

This guide covers how to set up multilingual audio playback in OpenEdX using the ``xblock_video`` component.

Overview of Supported Options
-----------------------------

Native HTML5 ``<video>`` does not support switching audio tracks from a single standalone ``.mp4`` file in modern browsers (Chrome and Firefox do not implement the ``AudioTrackList`` API).

Therefore, two cross-browser options are supported:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Approach
     - Technology
     - Learner Experience
   * - **Option 1: HLS Audio Groups** (Recommended)
     - Single master video with multi-language HLS manifest (``#EXT-X-MEDIA`` audio renditions via ``hls.js``)
     - **Seamless real-time switching** without pausing, buffering, or seeking
   * - **Option 2: Multiple MP4 Files**
     - Separate ``.mp4`` files per language
     - Source swap with **automatic playback timestamp preservation**


Option 1: HLS Stream with Multiple Audio Tracks (Recommended)
-------------------------------------------------------------

Converting a Multi-Audio MP4 with FFmpeg
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a multi-audio MP4 (e.g., audio track 0 is English and track 1 is French):

.. code-block:: bash

    ffmpeg -i input_multilang.mp4 \
      -map 0:v:0 -map 0:a:0 -map 0:a:1 \
      -c:v copy -c:a aac -b:a 128k \
      -var_stream_map "v:0,agroup:aud a:0,agroup:aud,language:en,default:yes a:1,agroup:aud,language:fr,default:no" \
      -hls_time 6 \
      -hls_playlist_type vod \
      -master_pl_name master.m3u8 \
      -f hls "stream_%v.m3u8"

This generates:

- ``master.m3u8``: Master playlist containing the video and alternate audio groups
- ``stream_0.m3u8``: Video segments
- ``stream_1.m3u8``: English audio stream
- ``stream_2.m3u8``: French audio stream

Studio Configuration
~~~~~~~~~~~~~~~~~~~~

In Studio, edit the Video component under **Advanced**:

- **Video File URLs** (``html5_sources``):

  .. code-block:: json

      ["https://cdn.example.com/videos/master.m3u8"]

- **Audio Tracks** (``audio_tracks``):

  .. code-block:: json

      [
        {"lang": "en", "label": "English"},
        {"lang": "fr", "label": "Français"}
      ]

*(Note: ``src`` is omitted; ``hls.js`` matches ``lang`` against the manifest's ``LANGUAGE`` attribute).*


Option 2: Multiple MP4 Files
----------------------------

Media Preparation
~~~~~~~~~~~~~~~~~

Export or encode separate ``.mp4`` files for each language:

- ``https://cdn.example.com/videos/lesson_en.mp4``
- ``https://cdn.example.com/videos/lesson_fr.mp4``
- ``https://cdn.example.com/videos/lesson_es.mp4``

Studio Configuration
~~~~~~~~~~~~~~~~~~~~

In Studio, edit the Video component under **Advanced**:

- **Video File URLs** (``html5_sources``):

  .. code-block:: json

      ["https://cdn.example.com/videos/lesson_en.mp4"]

- **Audio Tracks** (``audio_tracks``):

  .. code-block:: json

      [
        {"lang": "en", "label": "English", "src": "https://cdn.example.com/videos/lesson_en.mp4"},
        {"lang": "fr", "label": "Français", "src": "https://cdn.example.com/videos/lesson_fr.mp4"},
        {"lang": "es", "label": "Español", "src": "https://cdn.example.com/videos/lesson_es.mp4"}
      ]


Course XML (OLX) Example
------------------------

.. code-block:: xml

    <video url_name="intro_video"
           display_name="Course Introduction"
           download_video="true"
           html5_sources="[&quot;https://cdn.example.com/videos/master.m3u8&quot;]"
           audio_tracks="[
             {&quot;lang&quot;: &quot;en&quot;, &quot;label&quot;: &quot;English&quot;},
             {&quot;lang&quot;: &quot;fr&quot;, &quot;label&quot;: &quot;Français&quot;}
           ]">
    </video>


Player Accessibility & Controls
-------------------------------

When 2 or more audio tracks are configured:

- An **Audio** menu appears in the secondary controls toolbar.
- Keyboard support:
  - ``UP`` opens the menu.
  - ``UP`` / ``DOWN`` navigates available languages.
  - ``ENTER`` activates selection.
  - ``ESC`` closes the menu.
- Preferences are saved in the browser session (``audio_track_lang``) so subsequent videos will automatically select the learner's chosen language.
