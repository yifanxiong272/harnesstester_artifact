let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0009.emitExecSystemEvent', function() {
        it('should export a callable function', function() {
            assert.ok(testpilot_subject, 'module loaded');
            assert.ok(testpilot_subject.file_0009, 'file_0009 namespace exists');
            assert.strictEqual(typeof testpilot_subject.file_0009.emitExecSystemEvent, 'function',
                'emitExecSystemEvent should be a function');
        });

            })
})