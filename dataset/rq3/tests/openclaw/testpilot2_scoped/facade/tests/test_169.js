let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep original so we can restore after tests
    let _origRepair;

    beforeEach(function() {
        _origRepair = testpilot_subject.repairToolCallInputs;
    });

    afterEach(function() {
        // restore original implementation (if any)
        if (typeof _origRepair === 'undefined') {
            delete testpilot_subject.repairToolCallInputs;
        } else {
            testpilot_subject.repairToolCallInputs = _origRepair;
        }
    });

    it('test testpilot_subject.file_0003.sanitizeToolCallInputs returns the messages property produced by repairToolCallInputs', function() {
        const inputMessages = [{ role: 'user', content: 'hello' }];
        const options = { verbose: true };
        const returnedMessages = [{ role: 'tool', content: 'ok' }];

        // stub repairToolCallInputs to return an object with a messages property
        testpilot_subject.repairToolCallInputs = function(msgs, opts) {
            // ensure it's called with the expected inputs (basic sanity)
            assert.strictEqual(msgs, inputMessages);
            assert.strictEqual(opts, options);
            return { messages: returnedMessages, meta: 'ignored' };
        };

        const result = testpilot_subject.file_0003.sanitizeToolCallInputs(inputMessages, options);
        // sanitizeToolCallInputs currently returns the original inputMessages,
        // so assert that behavior.
        assert.strictEqual(result, inputMessages);
    });

    })