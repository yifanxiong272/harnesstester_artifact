let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0008.normalizeExecAsk as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0008);
        assert.strictEqual(typeof testpilot_subject.file_0008.normalizeExecAsk, 'function');
    });

    })