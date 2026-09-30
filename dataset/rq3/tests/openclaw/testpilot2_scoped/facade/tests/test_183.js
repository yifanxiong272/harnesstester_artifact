let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0005.processTool.execute', function() {
        it('should export an execute function', function() {
            assert.ok(testpilot_subject, 'module testpilot_subject is available');
            assert.ok(testpilot_subject.file_0005, 'file_0005 namespace exists');
            assert.ok(
                testpilot_subject.file_0005.processTool,
                'processTool exists on file_0005'
            );
            assert.strictEqual(
                typeof testpilot_subject.file_0005.processTool.execute,
                'function',
                'processTool.execute should be a function'
            );
        });

            })
})