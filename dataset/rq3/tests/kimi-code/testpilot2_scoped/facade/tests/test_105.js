let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.getExperimentalFeatures', function() {
        const KimiCore = testpilot_subject &&
                         testpilot_subject.file_0002 &&
                         testpilot_subject.file_0002.KimiCore;

        it('KimiCore should be available', function() {
            assert.ok(KimiCore, 'KimiCore constructor is not present at testpilot_subject.file_0002.KimiCore');
            assert.strictEqual(typeof KimiCore, 'function', 'KimiCore should be a constructor function');
            assert.strictEqual(typeof KimiCore.prototype.getExperimentalFeatures, 'function',
                'getExperimentalFeatures should be a function on KimiCore.prototype');
        });

            })
})