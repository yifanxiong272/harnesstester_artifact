let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.enterPlan', function() {
        it('should exist and be a function with one parameter', function() {
            assert.ok(testpilot_subject, 'module testpilot_subject should be present');
            assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
            assert.ok(testpilot_subject.file_0002.KimiCore, 'KimiCore should exist');
            const fn = testpilot_subject.file_0002.KimiCore.prototype.enterPlan;
            assert.strictEqual(typeof fn, 'function', 'enterPlan should be a function');
            // The declared signature in the prompt takes a single destructured object parameter
            assert.strictEqual(fn.length, 1, 'enterPlan should declare one parameter');
        });

            })
})