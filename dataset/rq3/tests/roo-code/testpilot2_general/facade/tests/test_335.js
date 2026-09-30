let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0007.parseApiReqStartedText', function() {
        const parse = testpilot_subject.file_0007.parseApiReqStartedText;

        it('should be a function', function() {
            assert.strictEqual(typeof parse, 'function');
        });

            })
})