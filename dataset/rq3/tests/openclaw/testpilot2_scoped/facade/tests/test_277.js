let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0008.validateHostEnv', function() {
    const validate = testpilot_subject &&
                     testpilot_subject.file_0008 &&
                     testpilot_subject.file_0008.validateHostEnv;

    it('validateHostEnv should exist and be a function', function() {
        assert.ok(validate, 'validateHostEnv is not defined');
        assert.strictEqual(typeof validate, 'function', 'validateHostEnv is not a function');
    });

    })