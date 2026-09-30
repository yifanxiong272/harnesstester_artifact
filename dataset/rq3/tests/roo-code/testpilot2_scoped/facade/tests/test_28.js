let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should expose file_0004.toolUseToText as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0004);
        assert.strictEqual(typeof testpilot_subject.file_0004.toolUseToText, 'function');
    });

    })