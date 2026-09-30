let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0008.resolveApprovalRunningNoticeMs;

    it('should floor positive non-integers and return integers unchanged', function(done) {
        assert.strictEqual(fn(3.9), 3);
        assert.strictEqual(fn(3.1), 3);
        assert.strictEqual(fn(5), 5);
        assert.strictEqual(fn(1.0), 1);
        done();
    });

    })