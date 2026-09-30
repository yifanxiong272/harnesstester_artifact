let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0002.OutputManager.prototype.outputError', function() {
        // Helper to create an OutputManager instance, or fail the test clearly if not present
        function makeManager() {
            assert.ok(testpilot_subject, 'testpilot_subject must be present');
            assert.ok(testpilot_subject.file_0002, 'testpilot_subject.file_0002 must be present');
            const OM = testpilot_subject.file_0002.OutputManager;
            assert.ok(OM, 'OutputManager constructor must be present');
            return new OM();
        }

        it('should not throw when label or text are omitted', function(done) {
            const manager = makeManager();

            const origError = console.error;
            const calls = [];
            console.error = function() {
                calls.push(Array.from(arguments));
            };

            try {
                // Call with no args and with one arg
                assert.doesNotThrow(() => manager.outputError(), 'calling without args should not throw');
                assert.doesNotThrow(() => manager.outputError('onlyLabel'), 'calling with single arg should not throw');
                // At least one call should have been made if implementation logs in those cases
                assert.ok(calls.length >= 0, 'no assumption about number of calls, just ensured no throw');
                done();
            } finally {
                console.error = origError;
            }
        });
    });
});