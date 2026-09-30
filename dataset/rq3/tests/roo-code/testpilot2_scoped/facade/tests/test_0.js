let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call convertToZAiFormat and handle either sync or Promise return values
    function callConvert(messages, options) {
        let res = testpilot_subject.file_0001.convertToZAiFormat(messages, options);
        if (res && typeof res.then === 'function') {
            return res;
        }
        return Promise.resolve(res);
    }

    it('convertToZAiFormat should exist and be a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0001, 'file_0001 should be present on module');
        assert.strictEqual(typeof testpilot_subject.file_0001.convertToZAiFormat, 'function',
            'convertToZAiFormat should be a function');
    });

    })