let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure tests have enough time in case the implementation uses timers
    this.timeout(5000);

    it('returns an error for unknown actions', async function() {
        // Call with an action that is not recognized by the implementation.
        // Include a sessionId so the implementation reaches the unknown-action check
        const result = await testpilot_subject.file_0005.processTool.execute('call-1', { action: 'no-such-action', sessionId: 'test-session' });

        // Expect a failed status and a message indicating the unknown action.
        assert.ok(result, 'expected a result object');
        assert.strictEqual(result.details && result.details.status, 'failed', 'expected status to be "failed"');
        const text = Array.isArray(result.content) && result.content[0] && result.content[0].text;
        assert.ok(typeof text === 'string', 'expected a text message in content');
        assert.ok(text.includes('Unknown action') && text.includes('no-such-action'), `unexpected message: ${text}`);
    });

})