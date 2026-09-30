let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0002.createAcpReplyProjector', function() {
    // Increase timeout since some internal timers/async ops might be used by the projector
    this.timeout(5000);

    function makeSpyDeliver() {
        const calls = [];
        const deliver = function(...args) {
            // Keep it async-safe (some internal callers await deliver)
            calls.push(args);
            return Promise.resolve();
        };
        return { deliver, calls };
    }

    it('returns an object with onEvent and flush functions', function() {
        const { deliver } = makeSpyDeliver();
        const proj = testpilot_subject.file_0002.createAcpReplyProjector({
            cfg: {}, provider: undefined, accountId: undefined,
            deliver, shouldSendToolSummaries: false
        });
        assert.strictEqual(typeof proj, 'object');
        assert.strictEqual(typeof proj.onEvent, 'function');
        assert.strictEqual(typeof proj.flush, 'function');
    });

    })