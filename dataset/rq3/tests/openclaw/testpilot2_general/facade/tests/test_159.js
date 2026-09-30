let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const makeMissing = testpilot_subject.file_0003.makeMissingToolResult;

    it('returns the expected structure and values when toolName is provided', function() {
        const before = Date.now();
        const result = makeMissing({ toolCallId: 'call-123', toolName: 'mytool' });
        const after = Date.now();

        assert.strictEqual(result.role, 'toolResult');
        assert.strictEqual(result.toolCallId, 'call-123');
        assert.strictEqual(result.toolName, 'mytool');
        assert.strictEqual(result.isError, true);

        assert.ok(Array.isArray(result.content), 'content should be an array');
        assert.strictEqual(result.content.length, 1, 'content should contain exactly one entry');
        assert.deepStrictEqual(result.content[0], {
            type: 'text',
            text: '[openclaw] missing tool result in session history; inserted synthetic error result for transcript repair.'
        });

        assert.strictEqual(typeof result.timestamp, 'number');
        // timestamp should be between before and after the call
        assert.ok(result.timestamp >= before && result.timestamp <= after, 'timestamp should be set to Date.now() at call time');
    });

    })