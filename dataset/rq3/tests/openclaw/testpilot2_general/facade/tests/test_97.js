let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isFailoverErrorMessage', function() {
        it('is a function', function(done) {
            assert.strictEqual(typeof testpilot_subject.file_0001.isFailoverErrorMessage, 'function');
            done();
        });

            })
})