let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.activateSkill basic checks', function() {
        it('should expose activateSkill on the prototype and it should be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0002, 'file_0002 namespace exists');
            assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore constructor exists');
            const fn = testpilot_subject.file_0002.KimiCore.prototype.activateSkill;
            assert.strictEqual(typeof fn, 'function', 'activateSkill is a function on the prototype');
        });

            })
})