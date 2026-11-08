/* eslint-env node */
'use strict';

const path = require('path');

const discussionRoot = __dirname;
const uiToolkitRoot = path.dirname(require.resolve('edx-ui-toolkit/package.json'));

module.exports = function (config) {
    config.set({
        basePath: discussionRoot,

        frameworks: ['jasmine'],

        files: [
            { pattern: require.resolve('jquery/dist/jquery.js'), included: true },
            { pattern: require.resolve('jasmine-jquery/lib/jasmine-jquery.js'), included: true },
            { pattern: require.resolve('underscore/underscore.js'), included: true },
            { pattern: require.resolve('backbone/backbone.js'), included: true },
            { pattern: path.join(uiToolkitRoot, 'src/js/utils/global-loader.js'), included: true },
            { pattern: path.join(uiToolkitRoot, 'src/js/utils/string-utils.js'), included: true },
            { pattern: path.join(uiToolkitRoot, 'src/js/utils/html-utils.js'), included: true },
            { pattern: 'static/spec/spec_helpers/i18n.js', included: true },
            { pattern: 'jasmine.common.conf.js', included: true },
            { pattern: require.resolve('draggabilly/dist/draggabilly.pkgd.js'), included: true },
            { pattern: 'static/js/vendor/URI.min.js', included: true },
            { pattern: 'static/js/vendor/jquery.leanModal.js', included: true },
            { pattern: 'static/js/vendor/Markdown.Converter.js', included: true },
            { pattern: 'static/js/vendor/Markdown.Sanitizer.js', included: true },
            { pattern: 'static/js/vendor/Markdown.Editor.js', included: true },
            { pattern: 'static/js/vendor/jquery.ajaxfileupload.js', included: true },
            { pattern: 'static/js/vendor/jquery.timeago.js', included: true },
            { pattern: 'static/js/vendor/jquery.truncate.js', included: true },
            { pattern: 'static/js/vendor/split.js', included: true },
            { pattern: 'static/js/mathjax_accessible.js', included: true },
            { pattern: 'static/js/mathjax_delay_renderer.js', included: true },
            { pattern: 'static/js/common/utils.js', included: true },
            { pattern: 'static/js/common/models/*.js', included: true },
            { pattern: 'static/js/common/content.js', included: true },
            { pattern: 'static/js/common/discussion.js', included: true },
            { pattern: 'static/js/common/mathjax_include.js', included: true },
            { pattern: 'static/js/customwmd.js', included: true },
            { pattern: 'static/js/common/views/*.js', included: true },
            { pattern: 'static/spec/spec_helpers/discussion_spec_helper.js', included: true },
            { pattern: 'static/spec/view/discussion_view_spec_helper.js', included: true },
            { pattern: 'static/spec/fixtures/**/*', included: false, served: true },
            { pattern: 'static/spec/**/*_spec.js', included: true }
        ],

        exclude: [
            '**/public/**'
        ],

        preprocessors: {
            'static/js/**/*.js': ['sourcemap'],
            'static/spec/view/discussion_thread_view_spec.js': ['regex', 'sourcemap'],
            'static/spec/**/*.js': ['sourcemap']
        },

        regexPreprocessor: {
            rules: [
                {
                    fileName: 'discussion_thread_view_spec.js',
                    replacement: [
                        { replace: /return function\(\) \{\s*/g, with: '' },
                        { replace: /            \};\s*\n        \}\);\s*\n        describe\('thread responses'/g, with: '        });\n        describe(\'thread responses\'' }
                    ]
                }
            ]
        },

        plugins: [
            'karma-regex-preprocessor',
            'karma-jasmine',
            'karma-chrome-launcher',
            'karma-firefox-launcher',
            'karma-sourcemap-loader',
            'karma-coverage',
            require('karma-spec-reporter')
        ],

        reporters: ['spec', 'coverage'],

        coverageReporter: {
            dir: 'coverage/',
            reporters: [
                { type: 'html', subdir: 'report-html' },
                { type: 'lcov', subdir: 'report-lcov' }
            ]
        },

        port: 9876,
        colors: true,
        logLevel: config.LOG_INFO,
        autoWatch: false,
        browsers: ['FirefoxNoUpdates'],

        customLaunchers: {
            FirefoxNoUpdates: {
                base: 'Firefox',
                prefs: {
                    'app.update.auto': false,
                    'app.update.enabled': false
                }
            }
        },

        singleRun: true,
        concurrency: Infinity,
        client: { captureConsole: true }
    });
};
