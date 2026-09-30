let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let KimiCore;

    before(function() {
        // Ensure the constructor exists on the module under test.
        if (!testpilot_subject ||
            !testpilot_subject.file_0002 ||
            !testpilot_subject.file_0002.KimiCore) {
            throw new Error('testpilot_subject.file_0002.KimiCore is not available');
        }
        KimiCore = testpilot_subject.file_0002.KimiCore;
    });

    // Helper that tries to create an instance without failing the test if the real constructor has side effects.
    function makeInstance() {
        try {
            return new KimiCore();
        } catch (e) {
            // If the real constructor requires arguments or does IO, create a bare object with the prototype so methods can be called.
            return Object.create(KimiCore.prototype);
        }
    }

    it('KimiCore.prototype.getCoreInfo exists and is a function', function() {
        assert.strictEqual(typeof KimiCore.prototype.getCoreInfo, 'function',
            'Expected getCoreInfo to be a function on the prototype');
    });

    })