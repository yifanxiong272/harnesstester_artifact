let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0005.processTool.execute', function() {
    // The implementation contains many dependencies (process registry, helpers, etc).
    // To keep tests self-contained and not rely on external resources, the tests below
    // exercise execution paths that do not require those dependencies:
    // - unknown action (falls through to the final default)
    // - missing sessionId (early validation before any registry calls)
    //
    // These are pure-function style checks of the returned shape and messages.

    it('returns Unknown action for an unrecognized action', async function() {
        const exec = testpilot_subject.file_0005.processTool.execute;
        // Provide a sessionId so the call doesn't fail early on validation.
        const result = await exec('call-1', { action: 'this-action-does-not-exist', sessionId: 'session-1' }, null, null);

        assert.ok(result && typeof result === 'object', 'result should be an object');
        assert.ok(Array.isArray(result.content), 'content should be an array');
        assert.strictEqual(result.content.length, 1, 'expected one content element');
        assert.strictEqual(result.content[0].type, 'text', 'content element should be text');
        assert.strictEqual(result.content[0].text, 'Unknown action this-action-does-not-exist');
        assert.ok(result.details && result.details.status === 'failed', 'status should be failed');
    });

});