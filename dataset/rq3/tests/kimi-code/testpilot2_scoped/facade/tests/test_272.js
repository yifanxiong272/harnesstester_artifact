let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.stopBackground', function() {
        let KimiCore;
        let fn;

        before(function() {
            // Ensure the module layout we expect exists
            assert.ok(testpilot_subject, 'testpilot_subject must be present');
            assert.ok(testpilot_subject.file_0002, 'testpilot_subject.file_0002 must be present');
            KimiCore = testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore constructor must be present');
            fn = KimiCore.prototype.stopBackground;
            assert.ok(fn, 'stopBackground must be present on prototype');
            assert.strictEqual(typeof fn, 'function', 'stopBackground must be a function');
        });

        it('has the expected declared arity (one parameter via destructuring)', function() {
            // The function signature stopBackground({sessionId,...payload}) declares one parameter
            assert.strictEqual(fn.length, 1, 'stopBackground should declare one parameter');
        });

            })
})