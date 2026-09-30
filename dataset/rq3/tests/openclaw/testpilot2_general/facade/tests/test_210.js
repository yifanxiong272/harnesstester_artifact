let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0008.applyPatch', function() {
        it('should be exported as a function', function() {
            assert.ok(testpilot_subject, 'module is present');
            assert.strictEqual(typeof testpilot_subject.file_0008.applyPatch, 'function',
                'applyPatch should be a function');
        });

            })
})