let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create an instance without forcing constructor side-effects.
    function makeInstance() {
        const ctor = testpilot_subject &&
                     testpilot_subject.file_0003 &&
                     testpilot_subject.file_0003.ToolCallComponent;
        if (!ctor) throw new Error('ToolCallComponent constructor not found on testpilot_subject.file_0003');
        try {
            // Prefer real constructor if it succeeds
            return new ctor();
        } catch (err) {
            // Fall back to a bare object with the correct prototype to avoid constructor side-effects.
            return Object.create(ctor.prototype);
        }
    }

    // Helper to call updateSubagentMetrics and normalize synchronous/Promise returns.
    function callUpdate(instance, payload) {
        let res;
        try {
            res = instance.updateSubagentMetrics(payload);
        } catch (err) {
            // Convert synchronous throw to a rejected Promise so tests using .then/.catch work uniformly.
            return Promise.reject(err);
        }
        if (res && typeof res.then === 'function') {
            return res;
        } else {
            return Promise.resolve(res);
        }
    }

    it('ToolCallComponent.prototype.updateSubagentMetrics exists and is a function', function() {
        assert.ok(testpilot_subject.file_0003, 'expected file_0003 to exist on testpilot_subject');
        const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'expected ToolCallComponent.prototype to exist');
        assert.strictEqual(typeof proto.updateSubagentMetrics, 'function',
            'expected updateSubagentMetrics to be a function on the prototype');
    });

    })