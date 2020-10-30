// provides webpack config for hot reload server build
const base = require('./webpack.config.base');
const webpack = require('webpack');
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = [
    Object.assign({}, base.main, { 
        mode: 'development',
        // put the dev server config in the main config since webpack-dev-server only 
        // looks at the first export for server config info
        devServer: {
            contentBase: path.join(__dirname, 'dist/render'),
            port: 9000,
            hot: true,
            watchContentBase: true
        }
    }),
    Object.assign({}, base.renderer, {
        mode: 'development',
        output: {
            filename: base.renderer.output.filename,
            path: base.renderer.output.path,
            publicPath: '/dist/render'
        },
        entry: {
            gui: [
                'webpack-dev-server/client?http://localhost:9000',
                'webpack/hot/only-dev-server',
                ...base.renderer.entry.gui
            ]
        },
        plugins: [
            ...base.renderer.plugins,
            new webpack.HotModuleReplacementPlugin()
        ]
    })
];