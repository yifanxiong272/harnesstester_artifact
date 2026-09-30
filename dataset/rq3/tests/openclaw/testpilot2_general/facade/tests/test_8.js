let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.extractLeadingHttpStatus;

    it('returns null when input does not start with an HTTP status', function() {
        assert.strictEqual(fn("not a status line"), null);
        assert.strictEqual(fn("Status: 200 OK"), null); // does not start with digits
        assert.strictEqual(fn(""), null);
    });

    })