let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Backup and set TOOL_CALL_TYPES for the duration of these tests
    let _origToolCallTypes;
    before(function() {
        _origToolCallTypes = global.TOOL_CALL_TYPES;
        // Define the set of types that count as tool calls for the tests
        global.TOOL_CALL_TYPES = new Set(['tool_call', 'plugin_call']);
    });

    after(function() {
        // Restore original global if any
        global.TOOL_CALL_TYPES = _origToolCallTypes;
    });

    it('returns empty array when msg.content is not an array', function(done) {
        const fn = testpilot_subject.file_0009.extractToolCallsFromAssistant;
        assert.deepStrictEqual(fn({ content: "not-an-array" }), []);
        assert.deepStrictEqual(fn({}), []); // no content property
        done();
    });

    })