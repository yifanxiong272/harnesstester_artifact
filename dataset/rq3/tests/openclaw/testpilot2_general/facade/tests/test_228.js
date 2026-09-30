let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.buildExecExitOutcome', function() {
        let fn = testpilot_subject && testpilot_subject.file_0009 && testpilot_subject.file_0009.buildExecExitOutcome;

        it('should export a function', function() {
            assert.strictEqual(typeof fn, 'function', 'buildExecExitOutcome should be a function');
        });

            })
})