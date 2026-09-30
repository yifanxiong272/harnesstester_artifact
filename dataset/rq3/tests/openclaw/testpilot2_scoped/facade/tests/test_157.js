let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.makeMissingToolResult', function() {
    it('returns correct structure when toolName is provided', function() {
        const params = { toolCallId: 'call-123', toolName: 'myTool' };
        const before = Date.now();
        const result = testpilot_subject.file_0003.makeMissingToolResult(params);
        const after = Date.now();

        // Basic shape
        assert.strictEqual(result.role, 'toolResult');
        assert.strictEqual(result.toolCallId, params.toolCallId);
        assert.strictEqual(result.toolName, params.toolName);

        // Content array and text
        assert.ok(Array.isArray(result.content), 'content should be an array');
        assert.strictEqual(result.content.length, 1);
        assert.deepStrictEqual(result.content[0], {
            type: 'text',
            text: '[openclaw] missing tool result in session history; inserted synthetic error result for transcript repair.'
        });

        // Error flag
        assert.strictEqual(result.isError, true);

        // Timestamp should be a number and within the test call window
        assert.strictEqual(typeof result.timestamp, 'number');
        assert.ok(result.timestamp >= before && result.timestamp <= after,
            `timestamp ${result.timestamp} should be between ${before} and ${after}`);
    });

    })