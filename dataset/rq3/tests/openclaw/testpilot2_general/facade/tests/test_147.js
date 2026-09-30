let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.parseApiErrorInfo', function() {
    const parse = (testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.parseApiErrorInfo)
        ? testpilot_subject.file_0001.parseApiErrorInfo
        : undefined;

    it('should exist and be a function', function() {
        assert.strictEqual(typeof parse, 'function', 'parseApiErrorInfo should be a function');
    });

    })