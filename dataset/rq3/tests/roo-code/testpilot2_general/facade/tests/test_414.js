let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0010.getMinComponentLines', function() {
        it('should exist and be a function', function(done) {
            try {
                assert.ok(testpilot_subject, 'testpilot_subject module is present');
                assert.ok(testpilot_subject.file_0010, 'file_0010 namespace is present');
                assert.strictEqual(typeof testpilot_subject.file_0010.getMinComponentLines, 'function',
                    'getMinComponentLines should be a function');
                done();
            } catch (err) { done(err); }
        });

            })
})