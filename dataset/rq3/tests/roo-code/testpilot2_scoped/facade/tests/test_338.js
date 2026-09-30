let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0013.sanitizeGeminiMessages as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0013);
        assert.strictEqual(typeof testpilot_subject.file_0013.sanitizeGeminiMessages, 'function');
    });

    })