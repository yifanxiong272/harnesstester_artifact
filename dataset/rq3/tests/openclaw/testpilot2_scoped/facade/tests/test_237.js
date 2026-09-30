let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Give async operations a little time if the implementation uses timers/events.
    this.timeout(2000);

    it('returns a thenable (Promise) or completes synchronously; both are acceptable', function() {
        const result = testpilot_subject.file_0008.emitExecSystemEvent('promise-check', {});
        if (result && typeof result.then === 'function') {
            // If a promise is returned, ensure it resolves (not rejects).
            return result;
        }
        // Otherwise treat lack of thrown error as success.
        return Promise.resolve();
    });
});