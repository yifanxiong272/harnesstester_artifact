let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // A small helper to create a fresh KimiCore instance and seed it with plugins
    function createCoreWithSeededPlugins() {
        // Construct a fresh instance. KimiCore implementations often expect an
        // rpcClient function passed into the constructor; provide a harmless stub
        // so tests don't fail with "rpcClient is not a function".
        let core = new testpilot_subject.file_0002.KimiCore(async function rpcClientStub() {
            // return a resolved promise / harmless result for any calls
            return {};
        });

        // Also ensure there is a rpcClient property on the instance in case the
        // implementation calls it as this.rpcClient(...)
        core.rpcClient = async function() { return {}; };

        // Provide multiple ways the implementation might store plugins so tests
        // remain robust regardless of whether the real implementation uses
        // .plugins, ._plugins (Map) or a getter method.
        core.plugins = {
            'pluginA': { id: 'pluginA', enabled: false }
        };

        core._plugins = new Map([['pluginB', { id: 'pluginB', enabled: true }]]);

        // Provide a generic getPlugin method that the implementation might call.
        // If the real implementation already has one, this will add/override it
        // for the purpose of the unit tests.
        core.getPlugin = function(id) {
            if (this.plugins && this.plugins[id]) return this.plugins[id];
            if (this._plugins && this._plugins.get(id)) return this._plugins.get(id);
            return undefined;
        };

        return core;
    }

    it('rejects when enabled is not a boolean', async function() {
        let core = createCoreWithSeededPlugins();

        // Non-boolean enabled should cause rejection/validation error.
        await assert.rejects(
            async () => { await core.setPluginEnabled({ id: 'pluginA', enabled: 'yes' }); },
            Error
        );
    });
});