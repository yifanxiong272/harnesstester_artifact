let mocha = require('mocha');
let assert = require('assert');

describe('test testpilot_subject', function() {
    // We'll require the module inside each test after setting up a controllable
    // global "import_ai" object so we can observe and stub its usage.
    // Helper to clear module cache and the global import_ai after each test.
    function clearModule() {
        try {
            delete require.cache[require.resolve('testpilot_subject')];
        } catch (e) {
            // ignore if not in cache
        }
        try {
            delete global.import_ai;
        } catch (e) {}
    }

    afterEach(function() {
        clearModule();
    });

    it('returns undefined for undefined or empty input', function() {
        // Ensure no import_ai is required for the "early return" path.
        clearModule();
        const testpilot_subject = require('..');

        // undefined input
        let res = testpilot_subject.file_0015.convertToolsForAiSdk();
        assert.strictEqual(res, undefined);

        // empty array input
        res = testpilot_subject.file_0015.convertToolsForAiSdk([]);
        assert.strictEqual(res, undefined);
    });

    })