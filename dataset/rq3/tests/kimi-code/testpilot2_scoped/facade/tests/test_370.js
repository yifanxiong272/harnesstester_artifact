let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the original method reference so we can call it with a fake `this`.
    const setPluginEnabled = testpilot_subject.file_0002.KimiCore.prototype.setPluginEnabled;

    it('waits for pluginsReady, calls assertPluginsLoaded, then calls plugins.setEnabled with given args', async function() {
        // Track order of events to ensure sequencing
        const order = [];

        // Create a controllable pluginsReady promise (deferred)
        let readyResolve;
        const pluginsReady = new Promise((resolve) => {
            readyResolve = () => {
                order.push('readyResolve');
                resolve();
            };
        });

        let assertPluginsLoadedCalled = false;
        const fakeThis = {
            pluginsReady,
            assertPluginsLoaded() {
                order.push('assertPluginsLoaded');
                assertPluginsLoadedCalled = true;
            },
            plugins: {
                setEnabled(id, enabled) {
                    order.push('setEnabled');
                    // verify the arguments are forwarded
                    assert.strictEqual(id, 'plugin-1');
                    assert.strictEqual(enabled, true);
                    return Promise.resolve();
                }
            }
        };

        // Call the method under test. It should await pluginsReady before proceeding.
        const p = setPluginEnabled.call(fakeThis, { id: 'plugin-1', enabled: true });

        // Give control back to the event loop to let any immediate code run.
        // At this point pluginsReady has not been resolved, so nothing should have happened yet.
        await new Promise((res) => setImmediate(res));
        assert.deepStrictEqual(order, [], 'No actions should occur before pluginsReady resolves');

        // Now resolve pluginsReady; the method should continue, call assertPluginsLoaded synchronously,
        // and then call plugins.setEnabled (which returns a Promise we await inside the method).
        readyResolve();

        // Await the method completion
        await p;

        // Verify the sequence and that assertPluginsLoaded was called before setEnabled
        assert.deepStrictEqual(order, ['readyResolve', 'assertPluginsLoaded', 'setEnabled']);
        assert.strictEqual(assertPluginsLoadedCalled, true);
    });

    })