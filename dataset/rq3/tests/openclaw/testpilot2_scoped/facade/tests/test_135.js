let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.parseApiErrorInfo', function() {
        it('should export a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0001);
            assert.strictEqual(typeof testpilot_subject.file_0001.parseApiErrorInfo, 'function');
        });

            })
})