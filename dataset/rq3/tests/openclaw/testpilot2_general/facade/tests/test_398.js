let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0014.extractToolErrorMessage', function() {
        it('does not throw when called with undefined and returns a stable value (null/undefined/string)', function(done) {
            assert.doesNotThrow(function() {
                var r = testpilot_subject.file_0014.extractToolErrorMessage(undefined);
                // Accept null/undefined or a string as a reasonable contract for "no error"
                assert.ok(r === undefined || r === null || typeof r === 'string');
            });
            done();
        });

            })
})