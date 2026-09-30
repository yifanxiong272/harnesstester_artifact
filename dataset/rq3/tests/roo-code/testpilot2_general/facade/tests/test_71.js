let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.generateCodeVerifier', function() {
        it('should return a string', function() {
            let v = testpilot_subject.file_0001.generateCodeVerifier();
            assert.strictEqual(typeof v, 'string', 'generateCodeVerifier should return a string');
        });

            })
})