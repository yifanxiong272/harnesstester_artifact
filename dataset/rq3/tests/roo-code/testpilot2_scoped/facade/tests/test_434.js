let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0022.tiktoken', function() {
    // Helper to get the function under test
    const tiktoken = testpilot_subject.file_0022.tiktoken;
    const subject = testpilot_subject.file_0022;

    afterEach(function() {
        // Restore/clear any test-injected values to avoid cross-test pollution
        try { delete subject.encoder } catch (_) {}
        try { delete subject.serializeToolUse } catch (_) {}
        try { delete subject.serializeToolResult } catch (_) {}
        try { delete subject.TOKEN_FUDGE_FACTOR } catch (_) {}
    });

    it('returns 0 for empty content array', async function() {
        // no encoder needed for this path
        const result = await tiktoken([]);
        assert.strictEqual(result, 0);
    });

    })