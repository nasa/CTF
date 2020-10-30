const base = require('./webpack.config.base')

module.exports = [
    Object.assign({}, base.main, { mode: 'production' }),
    Object.assign({}, base.renderer, { mode: 'production' })
];