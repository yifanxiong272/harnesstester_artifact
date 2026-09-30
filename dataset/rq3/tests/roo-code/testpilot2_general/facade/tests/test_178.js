let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep tests fast
    this.timeout(2000);

    it('returns undefined when prompt times out and no default provided', async function() {
        const pm = new testpilot_subject.file_0004.PromptManager();

        // Simulate a prompt that never resolves
        pm.prompt = function() {
            return new Promise(() => {});
        };

        const result = await pm.promptWithTimeout('Never resolves', 10);
        // The implementation returns an object with metadata; ensure the value is undefined and timedOut is true
        assert.strictEqual(result.value, undefined);
        assert.strictEqual(result.timedOut, true);
    });
});