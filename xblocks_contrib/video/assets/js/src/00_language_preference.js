'use strict';

/**
 * Keeps the video's transcript language and audio track in sync with the
 * learner's Open edX language preference.
 *
 * The platform preference is stored in the `openedx-language-preference`
 * cookie. Whenever it changes (compared with the value last seen by the
 * component), it overrides the previously remembered per-component choice,
 * provided that language is available. Otherwise the learner's own choice
 * (remembered in localStorage, which is shared by all same-origin iframes)
 * is kept.
 */
const COOKIE_NAME = 'openedx-language-preference';
const PREFIX = 'xblocks-language-preference:';

function getPlatformLanguage() {
    try {
        let cookie = _.find(document.cookie.split('; '), function(c) {
            return c.indexOf(COOKIE_NAME + '=') === 0;
        });
        if (cookie) {
            return decodeURIComponent(cookie.split('=')[1]).toLowerCase();
        }
    } catch (e) {
        // cookies unavailable
    }
    return null;
}

function readStorage(key) {
    try {
        return window.localStorage.getItem(PREFIX + key);
    } catch (e) {
        return null;
    }
}

function writeStorage(key, value) {
    try {
        window.localStorage.setItem(PREFIX + key, value);
    } catch (e) {
        // localStorage unavailable; the choice just won't persist.
    }
}

/**
 * Return the entry of `available` that matches `lang`: exact match first,
 * then by primary subtag (e.g. 'fr-ca' matches 'fr', and 'fr' matches 'fr-CA').
 * Returns the entry as spelled in `available`, or null.
 */
function matchLanguage(available, lang) {
    if (!lang) {
        return null;
    }
    lang = String(lang).toLowerCase().replace('_', '-');
    let base = lang.split('-')[0];
    let exact = _.find(available, function(a) {
        return String(a).toLowerCase().replace('_', '-') === lang;
    });
    if (exact) {
        return exact;
    }
    return _.find(available, function(a) {
        return String(a).toLowerCase().split(/[-_]/)[0] === base;
    }) || null;
}

/**
 * Decide which language to use for the component identified by `key`.
 *
 * @param {string} key        Component identifier ('transcript' or 'audio').
 * @param {string[]} available Languages that can be selected.
 * @return {string|null} Language to use, or null to keep the default.
 */
function resolve(key, available) {
    let platform = getPlatformLanguage();
    if (platform && readStorage('seen:' + key) !== platform) {
        writeStorage('seen:' + key, platform);
        let match = matchLanguage(available, platform);
        if (match) {
            writeStorage('choice:' + key, match);
            return match;
        }
    }
    return matchLanguage(available, readStorage('choice:' + key));
}

function remember(key, lang) {
    if (lang) {
        writeStorage('choice:' + key, lang);
    }
}

export default {resolve: resolve, remember: remember, matchLanguage: matchLanguage};
