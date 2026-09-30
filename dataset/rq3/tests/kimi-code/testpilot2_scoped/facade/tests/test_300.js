let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain the constructor safely
    function getKimiCoreConstructor() {
        if (!testpilot_subject || !testpilot_subject.file_0002) {
            throw new Error('testpilot_subject.file_0002 is not available');
        }
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        if (typeof KimiCore !== 'function') {
            throw new Error('KimiCore is not a constructor function');
        }
        return KimiCore;
    }

    it('KimiCore constructor and prototype.getUsage should exist', function() {
        const KimiCore = getKimiCoreConstructor();
        // The existence check is intentionally shallow: we only require the method to be present
        assert.strictEqual(typeof KimiCore, 'function', 'KimiCore should be a constructor function');
        assert.strictEqual(typeof KimiCore.prototype.getUsage, 'function', 'KimiCore.prototype.getUsage should be a function');
    });

    })