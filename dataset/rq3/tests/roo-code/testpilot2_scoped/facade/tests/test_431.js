let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0021.convertToResponsesApiInput', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0021 &&
               testpilot_subject.file_0021.convertToResponsesApiInput;

    it('should exist and be a function', function() {
        assert.ok(fn, 'convertToResponsesApiInput is not exported');
        assert.strictEqual(typeof fn, 'function');
    });

    })