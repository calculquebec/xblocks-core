const path = require('path');
const webpack = require('webpack');
const {CleanWebpackPlugin} = require('clean-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

const config = {
    entry: {
        'video-xblock': path.resolve(__dirname, 'js/src/10_main.js'),
    },
    output: {
        path: path.resolve(__dirname, '../public/js'),
        filename: '[name].js',
        clean: true,
        publicPath: '/'
    },
    resolve: {
        alias: {
            'edx-ui-toolkit/js': 'edx-ui-toolkit/src/js',
            'hls': 'hls.js/dist/hls.js'
        }
    },
    externals: {
        $: 'jQuery',
        jquery: 'jQuery',
        jQuery: 'jQuery'
    },
    plugins: [
        new CleanWebpackPlugin(),
        new webpack.DefinePlugin({
            'process.env.JS_ENV_EXTRA_CONFIG': JSON.parse(process.env.JS_ENV_EXTRA_CONFIG || '{}'),
            'CAPTIONS_CONTENT_TO_REPLACE': JSON.stringify(process.env.CAPTIONS_CONTENT_TO_REPLACE || ''),
            'CAPTIONS_CONTENT_REPLACEMENT': JSON.stringify(process.env.CAPTIONS_CONTENT_REPLACEMENT || '')
        }),
        new CopyWebpackPlugin({
            patterns: [
                {
                    from: 'css/video.css',
                    to: path.resolve(__dirname, '../public/css')
                }
            ]
        })
    ]
};

module.exports = config
