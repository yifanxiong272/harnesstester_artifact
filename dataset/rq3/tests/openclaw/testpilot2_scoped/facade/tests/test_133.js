let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isTransientHttpError', function() {
        it('should not throw and should return a boolean for empty-string input', function() {
            assert.doesNotThrow(() => {
                const res = testpilot_subject.file_0001.isTransientHttpError('');
                assert.strictEqual(typeof res, 'boolean', 'expected a boolean result for empty-string input');
            });
        });

            })
})