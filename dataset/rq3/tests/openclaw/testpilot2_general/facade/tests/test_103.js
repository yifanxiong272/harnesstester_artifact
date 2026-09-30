let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isImageDimensionErrorMessage', function() {
        const fn = testpilot_subject.file_0001.isImageDimensionErrorMessage;

        it('should be a function', function() {
            assert.strictEqual(typeof fn, 'function');
        });

            })
})