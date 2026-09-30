let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0011.createSubsystemLogger', function() {
    it('returns a logger object with expected methods and subsystem property', function() {
        const logger = testpilot_subject.file_0011.createSubsystemLogger('rootSubsystem');
        assert.strictEqual(typeof logger, 'object');
        assert.strictEqual(logger.subsystem, 'rootSubsystem');

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
        expectedMethods.forEach(m => {
            assert.strictEqual(typeof logger[m], 'function', `logger.${m} should be a function`);
        });
    });

    })