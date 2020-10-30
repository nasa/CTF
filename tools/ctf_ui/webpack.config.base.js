const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const common = {
    node: {
        __dirname: false,
        __filename: false
    },
    module: {
        rules: [
            {
                test: /\.(j|t)sx?$/,
                loader: 'babel-loader',
                options: {
                    babelrc: false,
                    presets: [
                        [
                            '@babel/preset-env',
                            { targets: { browsers: 'last 2 versions ' } }
                        ],
                        '@babel/preset-typescript',
                        '@babel/preset-react'
                    ],
                    plugins: [
                        ['@babel/plugin-proposal-class-properties', { loose: true }],
                    ]
                },
                exclude: /node_modules/
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            }
        ],
    },
    resolve: {
        extensions: ['.js', '.jsx', '.ts', '.tsx']
    }
}

const main = Object.assign({}, common, {
    target: 'electron-main',
    entry: { main: './src/electron/electron.ts' },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist/main')
    }
});

const renderer = Object.assign({}, common, {
    target: 'electron-renderer',
    entry: { gui: ['@babel/polyfill', './src/app/ui/index'] },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist/render'),
        publicPath: '../render/'
    },
    plugins: [new HtmlWebpackPlugin({title: "CFS Test Framework (Alpha)"})]
});

module.exports = {
    main: main,
    renderer: renderer
};