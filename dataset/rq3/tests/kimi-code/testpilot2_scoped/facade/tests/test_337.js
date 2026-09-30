let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain a usable instance of KimiCore.
    // Try calling the constructor with no args, with an empty object,
    // and fall back to Object.create of the prototype if construction fails.
    const KimiCore = testpilot_subject &&
                    testpilot_subject.file_0002 &&
                    testpilot_subject.file_0002.KimiCore;

    it('KimiCore and addAdditionalDir should exist', function() {
        assert.ok(KimiCore, 'KimiCore class not found on testpilot_subject.file_0002');
        assert.equal(typeof KimiCore.prototype.addAdditionalDir, 'function',
            'addAdditionalDir is not a function on KimiCore.prototype');
    });

    function makeCoreInstance() {
        try {
            return new KimiCore();
        } catch (e1) {
            try {
                return new KimiCore({});
            } catch (e2) {
                // Last resort: create an object with the correct prototype
                return Object.create(KimiCore.prototype);
            }
        }
    }

    })