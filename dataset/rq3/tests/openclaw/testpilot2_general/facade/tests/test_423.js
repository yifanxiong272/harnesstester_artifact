let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('createSubsystemLogger returns a logger object with expected shape and subsystem name', function() {
        const subsystem = 'unit-test-subsystem';
        const logger = testpilot_subject.file_0015.createSubsystemLogger(subsystem);
        assert.ok(logger && typeof logger === 'object', 'logger should be an object');
        assert.strictEqual(logger.subsystem, subsystem, 'logger.subsystem should match input');

        // expected methods
        const expectedMethods = [
            'isEnabled',
            'trace',
            'debug',
            'info',
            'warn',
            'error',
            'fatal',
            'raw',
            'child'
        ];
        for (const m of expectedMethods) {
            assert.strictEqual(typeof logger[m], 'function', `logger.${m} should be a function`);
        }
    });

    })