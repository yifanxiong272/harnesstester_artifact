let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // validateHostEnv is synchronous and throws on forbidden env keys.
    it('does not throw for an empty env', function() {
        assert.doesNotThrow(function() {
            testpilot_subject.file_0009.validateHostEnv({});
        });
    });

    })