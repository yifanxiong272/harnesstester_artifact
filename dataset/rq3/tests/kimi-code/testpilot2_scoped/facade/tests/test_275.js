let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain an instance of KimiCore if possible, otherwise use the prototype as a fallback context.
    function getKimiCoreInstance() {
        const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        if (!KimiCore) return null;
        try {
            return new KimiCore();
        } catch (e) {
            // If construction fails (requires args), use prototype as a fallback context.
            return KimiCore.prototype;
        }
    }

    it('should expose KimiCore.detachBackground as a function', function() {
        assert.ok(testpilot_subject.file_0002, 'file_0002 should exist on testpilot_subject');
        assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should exist on file_0002');
        assert.strictEqual(
            typeof testpilot_subject.file_0002.KimiCore.prototype.detachBackground,
            'function',
            'detachBackground should be a function on KimiCore.prototype'
        );
    });

    })