let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0007.applyPatch', function() {
    it('should export applyPatch as a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0007, 'file_0007 namespace should be present');
        assert.strictEqual(typeof testpilot_subject.file_0007.applyPatch, 'function', 'applyPatch should be a function');
    });

    })