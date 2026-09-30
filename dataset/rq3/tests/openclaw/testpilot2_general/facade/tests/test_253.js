let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.normalizeExecAsk - exists and is a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0009, 'file_0009 should be present on testpilot_subject');
        assert.strictEqual(typeof testpilot_subject.file_0009.normalizeExecAsk, 'function');
    });

    })