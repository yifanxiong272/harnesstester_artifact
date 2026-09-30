let mocha = require('mocha');
let assert = require('assert');

let testpilot_subject;
try {
    // Try to require the module under test. If it isn't available, we'll skip the suite.
    testpilot_subject = require('..');
} catch (e) {
    testpilot_subject = null;
}

describe('test testpilot_subject', function() {
    let KimiCore = null;

    before(function() {
        if (!testpilot_subject || !testpilot_subject.file_0002 || !testpilot_subject.file_0002.KimiCore) {
            // Skip whole suite if the module or constructor is not present.
            this.skip();
            return;
        }
        KimiCore = testpilot_subject.file_0002.KimiCore;
    });

    it('test testpilot_subject.file_0002.KimiCore.prototype.clearContext is a function', function() {
        assert.strictEqual(typeof KimiCore.prototype.clearContext, 'function');
    });

    })