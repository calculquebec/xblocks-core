Configuring Multilingual Videos (Audio Tracks, Subtitles & Transcripts)
======================================================================

This guide covers how to set up multilingual video playback in Open edX using the ``xblock_video`` component. It details:

1. **Multiple spoken audio tracks** (HLS audio renditions, separate MP4 files, or Course OLX).
2. **Multiple subtitles and transcripts** (closed captions and side transcript panel).
3. **Automatic synchronization** with the learner's platform language preference.

.. contents:: Table of Contents
   :local:
   :depth: 2


Overview & Browser Support
--------------------------

Native HTML5 ``<video>`` does not allow switching audio tracks from a single standalone ``.mp4`` file in modern browsers (Chrome and Firefox do not implement the HTML5 ``AudioTrackList`` API).

To provide cross-browser multilingual audio, ``xblock_video`` supports two workflows:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Approach
     - Technology
     - Learner Experience
   * - **Approach 1: HLS Audio Groups** (Recommended)
     - Single master video with multi-language HLS manifest (``#EXT-X-MEDIA`` audio renditions via ``hls.js``)
     - **Seamless real-time switching** without pausing, buffering, or seeking
   * - **Approach 2: Multiple MP4 Files**
     - Separate ``.mp4`` files per language
     - Source swap with **automatic playback timestamp preservation**


Configuring Spoken Audio Tracks
-------------------------------

Studio's standard Video editor does not feature an "Advanced" tab or raw JSON field for audio tracks. Therefore, audio tracks are configured directly using the standard video fields under the **Basic** tab (**Video URL** and **Fallback videos** / ``html5_sources``), or via Course OLX (XML).


Approach 1: Multi-Audio HLS Stream (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using an HLS stream (``.m3u8``), audio tracks are grouped into the stream manifest.

1. **Encoding Multi-Audio with FFmpeg**:
   If you have a multi-audio MP4 (e.g., track 0 is English and track 1 is French):

   .. code-block:: bash

       ffmpeg -i input_multilang.mp4 \
         -map 0:v:0 -map 0:a:0 -map 0:a:1 \
         -c:v copy -c:a aac -b:a 128k \
         -var_stream_map "v:0,agroup:aud a:0,agroup:aud,language:en,default:yes a:1,agroup:aud,language:fr,default:no" \
         -hls_time 6 \
         -hls_playlist_type vod \
         -master_pl_name master.m3u8 \
         -f hls "stream_%v.m3u8"

   This produces:
   - ``master.m3u8``: Master playlist containing the video and alternate audio groups
   - ``stream_0.m3u8``: Video stream
   - ``stream_1.m3u8``: English audio stream
   - ``stream_2.m3u8``: French audio stream

2. **Studio Configuration**:
   - In Studio, edit the Video component (**Basic** tab).
   - Enter your master playlist URL in **Video URL**:

     .. code-block:: text

         https://cdn.example.com/videos/master.m3u8

   - **Automatic detection**: The video player (`hls.js`) reads the ``#EXT-X-MEDIA:TYPE=AUDIO`` groups from the manifest and generates the **Audio** dropdown menu with localized language names (e.g., *English*, *Français*).
   - *(Optional manual language override)*: You can explicitly specify the track codes by appending ``#lang=en,fr`` to the URL:

     .. code-block:: text

         https://cdn.example.com/videos/master.m3u8#lang=en,fr


Approach 2: Multiple MP4 Files (Source Swap)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you produce separate standalone ``.mp4`` files for each language (e.g. ``lesson_en.mp4`` and ``lesson_fr.mp4``), the player swaps the video source while preserving the exact playback position (``currentTime``) and play/pause state.

In Studio (**Basic** tab):

1. **Option A: Using URL hash fragments (Recommended)**:
   - In **Video URL**, enter the primary language URL with ``#lang=<code>``:

     .. code-block:: text

         https://cdn.example.com/videos/lesson.mp4#lang=en

   - Under **Fallback videos**, add the alternate language URL(s):

     .. code-block:: text

         https://cdn.example.com/videos/lesson_fr.mp4#lang=fr

2. **Option B: Using filename suffixes**:
   - If files end with standard ISO language suffixes (e.g. ``_en.mp4``, ``_fr.mp4``, ``_es.mp4``), they are automatically recognized:
     - **Video URL**: ``https://cdn.example.com/videos/lesson_en.mp4``
     - **Fallback videos**: ``https://cdn.example.com/videos/lesson_fr.mp4``


Approach 3: Course OLX (XML Export/Import)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For courses authored or exported in OLX (XML), the ``audio_tracks`` attribute can be provided directly on the ``<video>`` element:

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

*(For MP4 source-swap in OLX, provide a ``src`` property on each track object).*


Configuring Subtitles & Transcripts
-----------------------------------

Open edX natively supports multiple subtitle and transcript tracks per video component. Subtitles (on-video Closed Captions / CC) and the interactive side-panel transcript are generated from the same transcript file.

In Studio:
1. Open the **Video** component and select the **Basic** tab.
2. Locate the **Transcript Languages** section.
3. Click **Add language** for each language needed (e.g. *French*, *English*, *Spanish*).
4. Upload the corresponding ``.srt`` or ``.vtt`` file for each language.
5. Save changes.

In the LMS player:
- The **CC** button toggles closed captions on and off on the video.
- Clicking the small arrow next to CC opens the subtitle language menu.
- The **Quotes** icon toggles the interactive side transcript panel.


Platform Language Preference Synchronization
--------------------------------------------

The video player automatically harmonizes the video's audio track, subtitles, and transcript panel with the learner's preferred platform language.

How Language Preference Sync Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Initial Load & Language Detection**:
   - Open edX sets an ``openedx-language-preference`` cookie when a learner chooses their site language (e.g., ``fr-ca``, ``fr``, ``en``).
   - When a video loads, it reads this cookie. If the user's platform language is available for this video:
     - The **Audio track** defaults to that language (if a matching audio stream or MP4 is configured).
     - The **Subtitles (CC)** and **Transcript panel** automatically default to that language (if a matching transcript was uploaded).
2. **Dialect & Subtag Matching**:
   - Matching supports both exact matches and base language tags:
     - A user with preference ``fr-ca`` will match ``fr-ca`` first, and fallback cleanly to ``fr``.
     - A user with preference ``en-us`` will match ``en``.
3. **Preserving Explicit Learner Overrides**:
   - If a learner manually changes the audio track or subtitles using the in-player menus, their manual choice is saved in browser storage (``audio_track_lang`` and ``language``).
   - The player respects this manual choice on subsequent videos and units.
   - The platform cookie only overrides the choice again if the learner **changes their site language** across the platform (e.g., switches the LMS language from French to English in the site header or account settings).


Player Controls & Keyboard Accessibility
----------------------------------------

When two or more audio tracks are available:

- An **Audio** menu button appears in the player's secondary controls toolbar.
- The menu lists all available spoken languages, highlighting the currently active track.
- **Keyboard Navigation**:
  - ``UP`` opens the audio language menu.
  - ``UP`` / ``DOWN`` arrows navigate through available languages.
  - ``ENTER`` or ``SPACE`` selects the focused track.
  - ``ESC`` closes the menu and returns focus to the audio button.
