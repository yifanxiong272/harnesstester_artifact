let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0014.extractMessagingToolSend', function() {
    // Helper to get the function under test and ensure it exists
    let fn = null;
    before(function() {
        assert.ok(testpilot_subject, 'testpilot_subject module must be present');
        assert.ok(testpilot_subject.file_0014, 'file_0014 namespace must be present on module');
        fn = testpilot_subject.file_0014.extractMessagingToolSend;
        assert.strictEqual(typeof fn, 'function', 'extractMessagingToolSend should be a function');
    });

    it('does not mutate the args object', function() {
        let toolName = 'exampleTool';
        let args = {
            to: 'user@example.com',
            body: 'Hello',
            meta: { priority: 'high', tags: ['a','b'] }
        };
        // deep copy to compare later
        let argsCopy = JSON.parse(JSON.stringify(args));

        // Call function (we only assert it does not throw)
        assert.doesNotThrow(() => { fn(toolName, args); });

        // original args must remain unchanged
        assert.deepStrictEqual(args, argsCopy, 'input args must not be mutated by extractMessagingToolSend');
    });

    })