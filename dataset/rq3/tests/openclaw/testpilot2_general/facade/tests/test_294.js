let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.validateHostEnv', function() {
    it('should export a function', function() {
        assert.strictEqual(
            typeof testpilot_subject.file_0009.validateHostEnv,
            'function',
            'validateHostEnv should be a function'
        );
    });

    })