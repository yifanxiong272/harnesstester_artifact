let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.beginCompaction', function() {
        it('should exist and be a function with arity 1', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            let KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
            assert.ok(KimiCore, 'KimiCore should be present on testpilot_subject.file_0002');
            let fn = KimiCore.prototype.beginCompaction;
            assert.strictEqual(typeof fn, 'function', 'beginCompaction should be a function');
            // Most definitions that destructure an object take a single argument
            assert.strictEqual(fn.length, 1, 'beginCompaction should declare exactly one parameter (the destructured object)');
        });

            })
})