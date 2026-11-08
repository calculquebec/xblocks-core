const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');

const discussionRoot = __dirname;
const staticJs = path.join(discussionRoot, 'static', 'js');
const staticCss = path.join(discussionRoot, 'static', 'css');

const config = {
  context: discussionRoot,
  entry: './static/js/discussion_main.js',
  output: {
    path: path.join(__dirname, '..', 'public', 'js'),
    filename: 'discussion_bundle.js',
  },
  resolve: {
    modules: [staticJs, 'node_modules'],
  },
  module: {
    rules: [
      {
        test: /Markdown\.Converter\.js$/,
        use: [
          {
            loader: 'append-prepend-loader',
            options: {
              append: '\n;window.Markdown=exports;',
            },
          },
        ],
      },
      {
        test: /Markdown\.Sanitizer\.js$/,
        use: [
          {
            loader: 'append-prepend-loader',
            options: {
              append: '\n;window.Markdown.getSanitizingConverter=exports.getSanitizingConverter;',
            },
          },
        ],
      },
      // Legacy IIFE code expects this===window; imports-loader wrapper (edx-platform pattern)
      // Exclude discussion_main.js (has top-level import/export).
      {
        test: /\.js$/,
        include: [
          path.join(staticJs, 'common'),
          path.join(staticJs, 'vendor'),
          path.join(staticJs, 'mathjax_accessible.js'),
          path.join(staticJs, 'mathjax_delay_renderer.js'),
          path.join(staticJs, 'customwmd.js'),
        ],
        exclude: [path.join(staticJs, 'discussion_main.js')],
        use: [
          {
            loader: 'imports-loader',
            options: 'this=>window'
          },
        ],
      },
      {
        test: /split\.js$/,
        use: [
          {
            loader: 'append-prepend-loader',
            options: {
              append: '\n;window._split=_split;',
            },
          },
        ],
      },
    ],
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: path.join(staticCss, 'inline-discussion.css'), to: path.join(__dirname, '..', 'public', 'css', 'inline-discussion.css') },
        { from: path.join(staticCss, 'inline-discussion-rtl.css'), to: path.join(__dirname, '..', 'public', 'css', 'inline-discussion-rtl.css') },
      ],
    }),
  ],
};

module.exports = config
