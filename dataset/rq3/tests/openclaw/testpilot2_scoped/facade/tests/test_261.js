let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0008.normalizeExecSecurity', function() {
        const fn = testpilot_subject.file_0008.normalizeExecSecurity;

        it('should be a function', function() {
            assert.strictEqual(typeof fn, 'function');
        });

            })
})