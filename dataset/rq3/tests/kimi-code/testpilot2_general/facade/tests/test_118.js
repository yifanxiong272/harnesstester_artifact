let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // shortcut to the method under test
    const ToolCallComponentProto = testpilot_subject.file_0003.ToolCallComponent.prototype;

    // Helper to create a minimal "instance" used as `this` for the prototype method
    function makeInstance(overrides = {}) {
        return Object.assign({
            // default behavior: eligible
            isDetachHintEligible: () => true,
            result: void 0,
            ui: { requestRender: () => { /* noop */ } },
            toolCall: { name: 'NonAgent' },
            detachHintVisible: false,
            detachHintTimer: void 0,
            rebuildBody: () => { /* noop */ }
        }, overrides);
    }

    // Keep original setTimeout for restoration
    const originalSetTimeout = global.setTimeout;
    const originalClearTimeout = global.clearTimeout;

    afterEach(function() {
        // restore globals in case tests mutated them
        global.setTimeout = originalSetTimeout;
        global.clearTimeout = originalClearTimeout;
    });

    it('does nothing when not eligible', function() {
        const inst = makeInstance({
            isDetachHintEligible: () => false,
            ui: { requestRender: () => { throw new Error('requestRender should not be called'); } },
            rebuildBody: () => { throw new Error('rebuildBody should not be called'); }
        });

        ToolCallComponentProto.startDetachHintTimer.call(inst);

        assert.strictEqual(inst.detachHintVisible, false);
        assert.strictEqual(inst.detachHintTimer, void 0);
    });

    })