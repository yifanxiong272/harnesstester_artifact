let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isImageDimensionErrorMessage', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0001, 'file_0001 namespace should exist');
            assert.strictEqual(typeof testpilot_subject.file_0001.isImageDimensionErrorMessage, 'function');
        });

            })
})