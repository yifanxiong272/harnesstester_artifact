let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.parseImageDimensionError', function() {
        it('should export a function', function() {
            assert.ok(testpilot_subject, 'module loaded');
            assert.ok(testpilot_subject.file_0001, 'file_0001 exists on module');
            assert.strictEqual(typeof testpilot_subject.file_0001.parseImageDimensionError, 'function',
                'parseImageDimensionError should be a function');
        });

            })
})