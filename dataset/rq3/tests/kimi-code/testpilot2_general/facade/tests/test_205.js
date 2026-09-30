let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call rebuildBody and handle sync/async returns uniformly.
    function callMaybeAsync(fn, ctx) {
        try {
            const out = fn.call(ctx);
            if (out && typeof out.then === 'function') {
                return out.then(r => ({ res: r, ctx }));
            } else {
                return Promise.resolve({ res: out, ctx });
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('should expose rebuildBody as a function on the prototype', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'expected file_0003 to exist');
        const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'expected ToolCallComponent.prototype to exist');
        assert.strictEqual(typeof proto.rebuildBody, 'function', 'rebuildBody should be a function');
    });

    })