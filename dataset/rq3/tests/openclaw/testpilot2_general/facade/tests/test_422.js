let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0015.createSubsystemLogger', function() {
    it('exports createSubsystemLogger as a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be available');
        assert.ok(testpilot_subject.file_0015, 'module testpilot_subject.file_0015 should be available');
        const createSubsystemLogger = testpilot_subject.file_0015.createSubsystemLogger;
        assert.ok(createSubsystemLogger, 'createSubsystemLogger should be exported');
        assert.strictEqual(typeof createSubsystemLogger, 'function', 'createSubsystemLogger should be a function');
    });

    })