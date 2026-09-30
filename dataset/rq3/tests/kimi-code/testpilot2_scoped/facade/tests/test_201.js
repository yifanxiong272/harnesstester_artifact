let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic presence / shape test
    it('test testpilot_subject.file_0002.KimiCore.prototype.cancel - exists and has expected arity', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should be present');
        const cancel = testpilot_subject.file_0002.KimiCore.prototype.cancel;
        assert.ok(typeof cancel === 'function', 'cancel should be a function');
        // The function signature in the prompt is cancel({sessionId,...payload})
        // which counts as a single declared parameter
        assert.strictEqual(cancel.length, 1, 'cancel should declare 1 parameter (destructured object)');
    });

    // Test that calling cancel returns a thenable (Promise-like) and does not synchronously throw
    })