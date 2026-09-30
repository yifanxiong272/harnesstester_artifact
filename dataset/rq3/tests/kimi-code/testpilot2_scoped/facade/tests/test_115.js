let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.resumeSessionWithOverrides', function() {
        // helper to get an instance of KimiCore; if constructor requires args or throws,
        // fall back to a plain object whose prototype is KimiCore.prototype so the method can still be invoked.
        function makeInstance() {
            let KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore must be present on testpilot_subject.file_0002');
            try {
                return new KimiCore();
            } catch (err) {
                // fallback to prototype-only object so the method can be invoked with a benign "this"
                return Object.create(KimiCore.prototype);
            }
        }

        it('should export the resumeSessionWithOverrides function on the prototype', function() {
            let KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore class exists');
            assert.ok(KimiCore.prototype, 'KimiCore.prototype exists');
            assert.strictEqual(typeof KimiCore.prototype.resumeSessionWithOverrides, 'function', 'resumeSessionWithOverrides should be a function');
        });

            })
})