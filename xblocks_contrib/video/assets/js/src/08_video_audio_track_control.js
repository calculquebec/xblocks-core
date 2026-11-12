'use strict';

import HtmlUtils from 'edx-ui-toolkit/js/utils/html-utils';
import Iterator from './00_iterator.js';

/**
 * Video Audio Track Control module.
 *
 * Renders an audio-track selector in the player's secondary controls bar.
 * Supports two switching strategies, selected automatically at runtime:
 *
 *   Path A — HLS audio groups (seamless, no seek needed):
 *     Requires an HLS manifest with #EXT-X-MEDIA audio renditions.
 *     Uses hls.js's hls.audioTracks / hls.audioTrack API.
 *     'lang' in the config entry must match the LANGUAGE attribute of the
 *     desired EXT-X-MEDIA tag in the manifest.
 *
 *   Path B — Separate source files per language (source-swap):
 *     Each audio track entry must supply a 'src' URL pointing to an .mp4
 *     (or other HTML5-compatible) file for that language. On track switch
 *     the player saves the current time, swaps the src, waits for metadata
 *     to load, then seeks back and resumes if playback was active.
 *
 * Config (state.config.audioTracks) is a list of objects:
 *   [
 *     { "lang": "en", "label": "English" },              // HLS path (no src)
 *     { "lang": "fr", "label": "Français", "src": "…" } // source-swap path
 *   ]
 *
 * Both objects may appear in the same list; strategy is chosen per-switch
 * based on (a) whether hls.js is active and (b) whether a 'src' is supplied.
 *
 * @exports video/08_video_audio_track_control.js
 * @constructor
 * @param {object} state  The video player state object.
 * @return {jquery Promise}
 */
function VideoAudioTrackControl(state) {
    if (!(this instanceof VideoAudioTrackControl)) {
        return new VideoAudioTrackControl(state);
    }

    _.bindAll(this,
        'clickMenuHandler', 'keyDownMenuHandler',
        'mouseEnterHandler', 'mouseLeaveHandler',
        'clickTrackHandler', 'keyDownTrackHandler',
        'destroy'
    );

    this.state = state;
    this.state.videoAudioTrackControl = this;
    this.initialize();

    return $.Deferred().resolve().promise();
}

VideoAudioTrackControl.moduleName = 'VideoAudioTrackControl';

VideoAudioTrackControl.prototype = {

    template: [
        '<div class="audio-tracks menu-container" role="application">',
        '  <p class="sr instructions" id="audio-track-instructions-{id}">',
        gettext('Press UP to open the audio language menu, then use the UP and DOWN arrow keys to navigate languages, then press ENTER to select.'),
        '  </p>',
        '  <button class="control audio-track-button" ',
        '    aria-disabled="false" aria-expanded="false" ',
        '    aria-describedby="audio-track-instructions-{id}" ',
        '    title="', gettext('Select audio language'), '">',
        '    <span class="icon fa fa-volume-up" aria-hidden="true"></span>',
        '    <span class="label">', gettext('Audio'), '</span>',
        '    <span class="value"></span>',
        '  </button>',
        '  <ol class="video-audio-tracks menu" role="menu"></ol>',
        '</div>'
    ].join(''),

    destroy: function() {
        if (this.el) {
            this.el.off({
                mouseenter: this.mouseEnterHandler,
                mouseleave: this.mouseLeaveHandler,
                click: this.clickMenuHandler,
                keydown: this.keyDownMenuHandler
            });
            this.closeMenu(true);
            this.tracksContainer.remove();
            this.el.remove();
        }
        this.state.el.off('destroy', this.destroy);
        delete this.state.videoAudioTrackControl;
    },

    initialize: function() {
        let self = this;
        let tracks = this.state.config.audioTracks;
        let player = this.state.videoPlayer && this.state.videoPlayer.player;
        let hls = player && player.hls;

        // If tracks are already provided via config (from #lang=..., _fr.mp4/_en.mp4, or OLX),
        // mount immediately.
        if (tracks && tracks.length >= 2) {
            this._mountControl(tracks);
            if (hls) {
                this._applySavedTrackWhenHLSReady(hls);
            } else if (player && this.currentTrack && this.currentTrack.src && this.currentTrack.src !== tracks[0].src) {
                this._applyInitialSource(player, this.currentTrack.src);
            }
            return true;
        }

        // Otherwise, if playing an HLS stream (.m3u8), auto-discover audio tracks from the manifest.
        if (hls) {
            if (hls.audioTracks && hls.audioTracks.length >= 2) {
                let discovered = this._extractTracksFromHLS(hls.audioTracks);
                if (discovered.length >= 2) {
                    this._mountControl(discovered);
                    this._switchViaHLS(hls, this.currentTrack.lang);
                    return true;
                }
            }
            let onHlsTracksReady = function() {
                if (self.el || !hls.audioTracks || hls.audioTracks.length < 2) {
                    return;
                }
                let discovered = self._extractTracksFromHLS(hls.audioTracks);
                if (discovered.length >= 2) {
                    self._mountControl(discovered);
                    self._switchViaHLS(hls, self.currentTrack.lang);
                }
            };
            hls.on('hlsManifestParsed', onHlsTracksReady);
            hls.on('hlsAudioTracksUpdated', onHlsTracksReady);
            return true;
        }

        return false;
    },

    _mountControl: function(tracks) {
        // Stamp unique id into template
        let html = this.template.replace(/\{id\}/g, this.state.id);
        this.el = $(html);
        this.tracksContainer = this.el.find('.video-audio-tracks');
        this.trackButton = this.el.find('.audio-track-button');

        // Restore previously saved language preference, or fall back to first track.
        let savedLang = (this.state.storage.getItem('audio_track_lang') || '').toLowerCase();
        this.currentTrack = _.find(tracks, function(t) {
            return (t.lang || '').toLowerCase() === savedLang;
        }) || tracks[0];

        this.render(tracks);
        this.bindHandlers();

        // Insert into secondary-controls, before the speed control if present.
        let secondaryControls = this.state.el.find('.secondary-controls');
        let speedControl = secondaryControls.find('.speeds');
        if (speedControl.length) {
            this.el.insertBefore(speedControl);
        } else {
            secondaryControls.append(this.el);
        }

        this.state.el.on('destroy', this.destroy);
    },

    _extractTracksFromHLS: function(hlsAudioTracks) {
        let seenLangs = {};
        let tracks = [];
        _.each(hlsAudioTracks, function(t, idx) {
            let lang = (t.lang || t.language || t.name || String(t.id !== undefined ? t.id : idx)).trim();
            let key = lang.toLowerCase();
            if (seenLangs[key]) {
                return;
            }
            seenLangs[key] = true;
            let label = '';
            try {
                if (typeof Intl !== 'undefined' && Intl.DisplayNames) {
                    let dn = new Intl.DisplayNames([lang], {type: 'language'});
                    let resolved = dn.of(lang);
                    if (resolved && resolved.toLowerCase() !== key) {
                        label = resolved.charAt(0).toUpperCase() + resolved.slice(1);
                    }
                }
            } catch (e) {
                // Ignore Intl errors for non-standard language tags
            }
            if (!label) {
                let rawName = (t.name || '').trim();
                label = rawName ? (rawName.charAt(0).toUpperCase() + rawName.slice(1)) : lang.toUpperCase();
            }
            tracks.push({
                lang: lang,
                label: label,
                src: ''
            });
        });
        return tracks;
    },

    _applySavedTrackWhenHLSReady: function(hls) {
        let self = this;
        let apply = function() {
            if (self.currentTrack && hls.audioTracks && hls.audioTracks.length >= 2) {
                self._switchViaHLS(hls, self.currentTrack.lang);
            }
        };
        if (hls.audioTracks && hls.audioTracks.length >= 2) {
            apply();
        } else {
            hls.on('hlsManifestParsed', _.once(apply));
        }
    },

    _applyInitialSource: function(player, src) {
        if (!player || !player.video) {
            return;
        }
        let sep = src.indexOf('?') === -1 ? '?' : '&';
        let urlWithTimestamp = src + sep + '_t=' + Date.now();
        if (player.videoEl) {
            player.videoEl.find('source').first().attr('src', urlWithTimestamp);
        }
        player.video.src = urlWithTimestamp;
        player.video.load();
    },

    /**
     * Render the track list inside the dropdown menu.
     */
    render: function(tracks) {
        let self = this;
        let items = _.map(tracks, function(track) {
            let isCurrent = track.lang === self.currentTrack.lang;
            return HtmlUtils.interpolateHtml(
                HtmlUtils.HTML(
                    '<li role="menuitem" class="' + (isCurrent ? 'is-active' : '') + '">' +
                    '<button type="button" class="control audio-option" ' +
                    'data-lang="{lang}" ' +
                    'data-src="{src}" ' +
                    'aria-checked="{checked}" ' +
                    'role="menuitemradio">' +
                    '{label}' +
                    '</button></li>'
                ),
                {
                    lang: track.lang,
                    src: track.src || '',
                    checked: isCurrent ? 'true' : 'false',
                    label: track.label
                }
            );
        });

        this.tracksContainer.html(
            _.map(items, function(item) { return HtmlUtils.ensureHtml(item).toString(); }).join('')
        );

        // Set the button label to the current track
        this.trackButton.find('.value').text(this.currentTrack.label);

        // Build an Iterator over the menu items for keyboard navigation
        this.trackIterator = new Iterator(this.tracksContainer.find('.audio-option').toArray());
    },

    bindHandlers: function() {
        this.el.on({
            mouseenter: this.mouseEnterHandler,
            mouseleave: this.mouseLeaveHandler,
            click: this.clickMenuHandler,
            keydown: this.keyDownMenuHandler
        });

        this.tracksContainer.on('click', '.audio-option', this.clickTrackHandler);
        this.tracksContainer.on('keydown', '.audio-option', this.keyDownTrackHandler);
    },

    // -------------------------------------------------------------------------
    // Audio switching — the two paths
    // -------------------------------------------------------------------------

    /**
     * Switch to a new audio track.
     * Automatically picks HLS path (A) or source-swap path (B).
     *
     * @param {string} lang  BCP-47 language code (e.g. 'fr')
     * @param {string} src   URL to separate .mp4, or empty string for HLS path
     * @param {string} label Human-readable label for UI update
     */
    switchTrack: function(lang, src, label) {
        let player = this.state.videoPlayer.player;
        let hlsInstance = player && player.hls;

        if (hlsInstance && !src) {
            // ---- Path A: HLS audio-groups ----
            this._switchViaHLS(hlsInstance, lang);
        } else if (src) {
            // ---- Path B: source-swap ----
            this._switchViaSourceSwap(player, src);
        } else {
            console.warn('[AudioTrackControl] No HLS instance and no src URL for lang:', lang);
            return;
        }

        // Update state and UI
        this.currentTrack = {lang: lang, label: label, src: src};
        this.trackButton.find('.value').text(label);
        this.tracksContainer.find('.audio-option').each(function() {
            let isThis = $(this).data('lang') === lang;
            $(this)
                .attr('aria-checked', isThis ? 'true' : 'false')
                .closest('li').toggleClass('is-active', isThis);
        });

        // Persist preference in player storage
        this.state.storage.setItem('audio_track_lang', lang);

        // Notify other modules (e.g. analytics)
        this.state.el.trigger('audio_track:changed', {lang: lang, label: label, path: hlsInstance && !src ? 'hls' : 'source-swap'});
    },

    /**
     * Path A: Switch audio track via hls.js audio-groups API.
     * hls.js will seamlessly switch the audio rendition; no seek is needed.
     *
     * @param {Hls}    hls   The hls.js instance from player.hls
     * @param {string} lang  BCP-47 lang to match against HLS manifest LANGUAGE
     */
    _switchViaHLS: function(hls, lang) {
        let audioTracks = hls.audioTracks || [];
        let target = _.find(audioTracks, function(t) {
            // hls.js exposes `lang` or `language` depending on version
            return (t.lang || t.language || '').toLowerCase() === lang.toLowerCase()
                || t.name === lang;
        });

        if (target !== undefined) {
            console.log('[AudioTrackControl] HLS path: switching to audio track id', target.id, 'lang', lang);
            hls.audioTrack = target.id;
        } else {
            console.warn('[AudioTrackControl] HLS path: no audio track found for lang', lang,
                '. Available tracks:', audioTracks);
        }
    },

    /**
     * Path B: Switch audio by swapping the <video> src.
     * Saves current playback position, loads new src, seeks back, resumes.
     *
     * @param {object} player  The HTML5Video.Player instance
     * @param {string} src     URL to the .mp4 for this language
     */
    _switchViaSourceSwap: function(player, src) {
        let self = this;
        let video = player.video;
        let currentTime = video.currentTime || 0;
        let wasPlaying = !video.paused;

        console.log('[AudioTrackControl] Source-swap path: loading', src,
            'restoring time', currentTime, 'wasPlaying', wasPlaying);

        // Pause before swap to avoid browser autoplay conflicts
        if (wasPlaying) {
            video.pause();
        }

        // Swap source (append cache-buster so browsers do not serve stale content)
        let sep = src.indexOf('?') === -1 ? '?' : '&';
        video.src = src + sep + '_t=' + Date.now();
        video.load();

        // Once metadata is available, seek and optionally resume
        video.addEventListener('loadedmetadata', function handler() {
            video.removeEventListener('loadedmetadata', handler);

            if (self.state.speed && $.isFunction(player.setPlaybackRate)) {
                player.setPlaybackRate(self.state.speed);
            }

            // Clamp restore time to new video duration
            let seekTo = Math.min(currentTime, video.duration || 0);
            video.currentTime = seekTo;

            if (wasPlaying) {
                let playPromise = video.play();
                if (playPromise !== undefined) {
                    playPromise.catch(function(err) {
                        console.warn('[AudioTrackControl] play() after source-swap failed:', err);
                    });
                }
            }
        });
    },

    // -------------------------------------------------------------------------
    // Menu open/close
    // -------------------------------------------------------------------------

    openMenu: function() {
        this.el.addClass('is-opened');
        this.trackButton.attr('aria-expanded', 'true');
        this.tracksContainer.show();
        // Focus the currently active item
        let activeOption = this.tracksContainer.find('li.is-active .audio-option');
        if (activeOption.length) {
            activeOption.focus();
            this.trackIterator.setCurrent(activeOption[0]);
        } else {
            this.tracksContainer.find('.audio-option').first().focus();
        }
    },

    closeMenu: function(immediate) {
        this.el.removeClass('is-opened');
        this.trackButton.attr('aria-expanded', 'false');
        if (immediate) {
            this.tracksContainer.hide();
        } else {
            this.tracksContainer.hide();
        }
        this.trackButton.focus();
    },

    isMenuOpen: function() {
        return this.trackButton.attr('aria-expanded') === 'true';
    },

    // -------------------------------------------------------------------------
    // Event handlers
    // -------------------------------------------------------------------------

    clickMenuHandler: function(event) {
        // Clicks on track options are handled by clickTrackHandler
        if ($(event.target).closest('.audio-option').length) {
            return;
        }
        event.preventDefault();
        if (this.isMenuOpen()) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    },

    keyDownMenuHandler: function(event) {
        // UP arrow on the button opens the menu
        if (event.which === 38 && !this.isMenuOpen()) {
            event.preventDefault();
            this.openMenu();
        }
        // ESC closes the menu
        if (event.which === 27 && this.isMenuOpen()) {
            event.preventDefault();
            this.closeMenu();
        }
    },

    clickTrackHandler: function(event) {
        event.preventDefault();
        let link = $(event.currentTarget);
        let lang = link.data('lang');
        let src  = link.data('src') || '';
        let label = link.text().trim();
        this.closeMenu();
        this.switchTrack(lang, src, label);
    },

    keyDownTrackHandler: function(event) {
        // UP / DOWN navigate; ENTER selects; ESC closes
        let key = event.which;
        if (key === 40) { // DOWN
            event.preventDefault();
            this.trackIterator.next();
            $(this.trackIterator.getCurrent()).focus();
        } else if (key === 38) { // UP
            event.preventDefault();
            this.trackIterator.prev();
            $(this.trackIterator.getCurrent()).focus();
        } else if (key === 13) { // ENTER
            event.preventDefault();
            $(this.trackIterator.getCurrent()).trigger('click');
        } else if (key === 27) { // ESC
            event.preventDefault();
            this.closeMenu();
        }
    },

    mouseEnterHandler: function() {
        // Keep focus visible on hover — no auto-open needed
    },

    mouseLeaveHandler: function() {
        // Close menu when mouse leaves the whole control
        if (this.isMenuOpen()) {
            this.closeMenu();
        }
    }
};

export default VideoAudioTrackControl;
