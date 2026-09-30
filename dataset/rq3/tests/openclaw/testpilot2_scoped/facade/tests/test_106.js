let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isOverloadedErrorMessage', function() {
        const fn = testpilot_subject.file_0001.isOverloadedErrorMessage;

        it('should exist and be a function', function() {
            assert.strictEqual(typeof fn, 'function', 'isOverloadedErrorMessage should be a function');
        });

            })
})