let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.stripToolResultDetails', function() {
        it('should return an empty array when given an empty array', function() {
            let messages = [];
            let result = testpilot_subject.file_0003.stripToolResultDetails(messages);
            // Expect a (deep) empty array result
            assert.deepStrictEqual(result, []);
        });

            })
})