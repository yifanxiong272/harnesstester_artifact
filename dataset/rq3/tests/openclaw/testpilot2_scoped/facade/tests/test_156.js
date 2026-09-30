let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.makeMissingToolResult', function() {
        it('is exported and is a function', function() {
            assert.ok(testpilot_subject, 'module should be present');
            assert.ok(testpilot_subject.file_0003, 'file_0003 should be present on module');
            assert.strictEqual(typeof testpilot_subject.file_0003.makeMissingToolResult, 'function',
                'makeMissingToolResult should be a function');
        });

            })
})