let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.renderExecHostLabel', function() {
    let fn;
    before(function() {
        // Ensure the path exists before running tests
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0008, 'testpilot_subject.file_0008 should be present');
        fn = testpilot_subject.file_0008.renderExecHostLabel;
    });

    it('should export a function', function() {
        assert.strictEqual(typeof fn, 'function', 'renderExecHostLabel should be a function');
    });

    })