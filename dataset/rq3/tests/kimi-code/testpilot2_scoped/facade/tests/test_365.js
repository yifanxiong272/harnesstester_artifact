let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;

    it('listPlugins resolves to plugins.summaries() result and calls assertPluginsLoaded before summaries', async function() {
        // create an object that uses the KimiCore prototype (avoid running constructor)
        let core = Object.create(KimiCore.prototype);

        // record call order
        let calls = [];

        core.pluginsReady = Promise.resolve();
        core.assertPluginsLoaded = function() { calls.push('assert'); };
        core.plugins = {
            summaries: function() { calls.push('summaries'); return ['pluginA', 'pluginB']; }
        };

        let result = await core.listPlugins();

        assert.deepStrictEqual(result, ['pluginA', 'pluginB']);
        assert.deepStrictEqual(calls, ['assert', 'summaries'], 'assertPluginsLoaded should be called before plugins.summaries');
    });

    })