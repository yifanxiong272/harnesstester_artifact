let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Small helper to create an instance of KimiCore without failing if the constructor requires args.
    function makeKimiCoreInstance(KimiCore) {
        try {
            return new KimiCore();
        } catch (e) {
            // Fall back to a bare object that uses the prototype so we can still call prototype methods.
            return Object.create(KimiCore.prototype);
        }
    }

    it('should expose KimiCore.prototype.prompt as a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should exist');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.strictEqual(typeof KimiCore.prototype.prompt, 'function', 'prompt should be a function on the prototype');
    });

    })