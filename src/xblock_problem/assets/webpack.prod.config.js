/* eslint-env node */
const { merge } = require('webpack-merge');
const devConfig = require('./webpack.config.js');
const TerserPlugin = require("terser-webpack-plugin");

module.exports = merge(devConfig, {
    mode: 'production',
    devtool: false, // Disable source maps for production
    optimization: {
        minimize: true,
        minimizer: [
            new TerserPlugin({
                parallel: true,
            }),
        ],
    },
});
