let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.forkSession (unit-level)', function() {
        let KimiCore;

        before(function() {
            // ensure the path exists so tests fail fast if module layout changed
            assert.ok(testpilot_subject, 'testpilot_subject module is required');
            assert.ok(testpilot_subject.file_0002, 'testpilot_subject.file_0002 exists');
            KimiCore = testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore constructor exists');
        });

        it('should expose forkSession on the prototype', function() {
            const has = Object.prototype.hasOwnProperty.call(KimiCore.prototype, 'forkSession');
            assert.strictEqual(has, true, 'KimiCore.prototype should have own property "forkSession"');
        });

            })
})