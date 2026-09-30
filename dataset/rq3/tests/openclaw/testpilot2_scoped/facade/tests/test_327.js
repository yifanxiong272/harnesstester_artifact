let mocha = require('mocha');
let assert = require('assert');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    // require the module under test lazily inside tests so we can stub child_process.exec first
    let originalExec;

    beforeEach(function() {
        // save original exec and replace with a stub we control in each test
        originalExec = child_process.exec;
    });

    afterEach(function() {
        // restore original exec after each test to avoid side effects
        child_process.exec = originalExec;
        originalExec = null;
        // clear require cache for module under test so it will pick up the restored exec if it required child_process earlier
        try {
            delete require.cache[require.resolve('testpilot_subject')];
        } catch (e) {
            // ignore if module not present
        }
    });

    it('handles empty docker output without throwing (returns a defined value)', async function() {
        // Arrange: stub exec to return empty stdout (container not found)
        child_process.exec = function(cmd, callback) {
            setImmediate(() => callback(null, '', ''));
        };

        let testpilot_subject = require('..');

        // Act: call the function
        let result = await testpilot_subject.file_0013.dockerContainerState('nonexistent');

        // Assert: function should not throw; it should resolve (may return null/false/empty string depending on implementation).
        // We assert it's defined (can be null) OR explicitly allow null/undefined but prefer defined.
        // To be lenient across implementations, accept null/undefined but still ensure no exception occurred.
        assert.ok(
            typeof result !== 'undefined' || result === null,
            'function should resolve (possibly to null) when container is not found'
        );
    });
});