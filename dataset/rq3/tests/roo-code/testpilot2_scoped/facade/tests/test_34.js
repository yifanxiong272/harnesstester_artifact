let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports a constructor for file_0006.MultiPointStrategy', function() {
        assert.ok(testpilot_subject, 'module should be present');
        const MultiPointStrategy = testpilot_subject.file_0006 && testpilot_subject.file_0006.MultiPointStrategy;
        assert.strictEqual(typeof MultiPointStrategy, 'function', 'MultiPointStrategy should be a function/constructor');
    });

    })