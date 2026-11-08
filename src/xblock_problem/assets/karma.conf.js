/* eslint-env node */
'use strict';

const path = require('path');

const uiToolkitRoot = path.dirname(require.resolve('edx-ui-toolkit/package.json'));

module.exports = function (config) {
    config.set({
        basePath: '',

        frameworks: ['jasmine'],

        files: [
            { pattern: require.resolve('jquery/dist/jquery.js'), included: true },
            { pattern: require.resolve('jasmine-jquery/lib/jasmine-jquery.js'), included: true },
            { pattern: require.resolve('underscore/underscore.js'), included: true },

            { pattern: 'static/js/vendor/codemirror-compressed.js', included: true },

            { pattern: path.join(uiToolkitRoot, 'src/js/utils/global-loader.js'), included: true },
            { pattern: path.join(uiToolkitRoot, 'src/js/utils/string-utils.js'), included: true },
            { pattern: path.join(uiToolkitRoot, 'src/js/utils/html-utils.js'), included: true },

            { pattern: 'spec_helpers/ajax_prefix.js', included: true },
            { pattern: 'spec_helpers/i18n.js', included: true },
            { pattern: 'spec_helpers/logger.js', included: true },
            { pattern: 'spec_helpers/accessibility_tools.js', included: true },
            { pattern: 'spec_helpers/add_ajax_prefix.js', included: true },
            { pattern: 'spec_helpers/helper.js', included: true },

            { pattern: 'spec_helpers/jasmine-waituntil.js', included: true },
            { pattern: 'spec_helpers/jasmine-extensions.js', included: true },
            { pattern: 'spec_helpers/jasmine-imagediff.js', included: true },

            { pattern: 'static/js/xmodule.js', included: true },
            { pattern: 'static/js/javascript_loader.js', included: true },
            { pattern: 'static/js/collapsible.js', included: true },
            { pattern: 'static/js/display.js', included: true },
            { pattern: 'static/js/imageinput.js', included: true },
            { pattern: 'static/js/schematic.js', included: true },

            { pattern: '../capa/static/js/capa/**/*.js', included: false },

            { pattern: '../capa/static/js/capa/src/jschannel.js', included: true },
            { pattern: '../capa/static/js/capa/src/jsinput.js', included: true },
            { pattern: '../capa/static/js/capa/src/formula_equation_preview.js', included: true },
            { pattern: '../capa/static/js/capa/symbolic_mathjax_preprocessor.js', included: true },
            { pattern: '../capa/static/js/capa/annotationinput.js', included: true },
            { pattern: '../capa/static/js/capa/choicetextinput.js', included: true },

            { pattern: 'fixtures/**/*.html', included: false, served: true },
            { pattern: 'fixtures/**/*.underscore', included: false, served: true },
            { pattern: '../capa/static/js/capa/fixtures/**/*.html', included: false, served: true },
            { pattern: '../capa/static/js/capa/genex/**/*', included: false, served: true },
            { pattern: '../capa/static/js/capa/protex/**/*', included: false, served: true },

            { pattern: 'spec/*_spec.js', included: true },
            { pattern: '../capa/static/js/capa/spec/*_spec.js', included: true },

            { pattern: 'karma_runner.js', included: true }
        ],

        exclude: [
            '**/public/**',
            '../capa/static/js/capa/jsinput/jsinput_example.js'
        ],
        proxies: {
            '/spec/javascripts/fixturesfixtures/js/capa/fixtures/': '/absolute' + path.resolve(__dirname, '../capa/static/js/capa/fixtures').replace(/\\/g, '/') + '/',
            '/spec/javascripts/fixturesfixtures/js/': '/base/static/js/',
            '/spec/javascripts/fixturesfixtures/': '/base/fixtures/',
        },

        preprocessors: {
            'static/js/**/*.js': ['sourcemap'],
            'spec/**/*.js': ['sourcemap']
        },

        plugins: [
            'karma-jasmine',
            'karma-requirejs',
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
