let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.sanitizeToolCallInputs - function exists', function(done) {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should be present');
        assert.strictEqual(typeof testpilot_subject.file_0003.sanitizeToolCallInputs, 'function',
            'sanitizeToolCallInputs should be a function');
        done();
    });

    })