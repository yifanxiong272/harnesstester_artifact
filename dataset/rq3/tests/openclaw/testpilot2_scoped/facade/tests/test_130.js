let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isTransientHttpError', function() {
        it('returns false for empty or whitespace-only input', function() {
            assert.strictEqual(testpilot_subject.file_0001.isTransientHttpError(''), false);
            assert.strictEqual(testpilot_subject.file_0001.isTransientHttpError('   \n\t'), false);
        });

            })
})