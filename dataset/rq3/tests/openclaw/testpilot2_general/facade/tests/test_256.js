let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns "sandbox" for exact lowercase "sandbox"', function(done) {
        const res = testpilot_subject.file_0009.normalizeExecHost('sandbox');
        assert.strictEqual(res, 'sandbox');
        done();
    });

    })