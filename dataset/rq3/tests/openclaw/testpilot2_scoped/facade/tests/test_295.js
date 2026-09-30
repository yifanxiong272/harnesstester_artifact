let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const createSubsystemLogger = testpilot_subject &&
                                   testpilot_subject.file_0011 &&
                                   testpilot_subject.file_0011.createSubsystemLogger;

    it('createSubsystemLogger should be a function', function() {
        assert.ok(createSubsystemLogger, 'createSubsystemLogger is not present');
        assert.strictEqual(typeof createSubsystemLogger, 'function', 'createSubsystemLogger should be a function');
    });

    })