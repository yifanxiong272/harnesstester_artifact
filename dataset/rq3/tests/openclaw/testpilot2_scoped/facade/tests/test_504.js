let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const SafeOpenError = testpilot_subject.file_0018.SafeOpenError;

    it('constructs an Error with the given message and code', function() {
        const err = new SafeOpenError(42, 'something went wrong');
        // Basic Error behavior
        assert.ok(err instanceof Error, 'should be an instance of Error');
        // Class identity
        assert.ok(err instanceof SafeOpenError, 'should be an instance of SafeOpenError');
        // name is set to "SafeOpenError"
        assert.strictEqual(err.name, 'SafeOpenError');
        // message is preserved
        assert.strictEqual(err.message, 'something went wrong');
        // code is preserved
        assert.strictEqual(err.code, 42);
        // toString should include name and message
        assert.ok(err.toString().startsWith('SafeOpenError: something went wrong'));
        // stack should be a string (environment dependent but usually present)
        assert.strictEqual(typeof err.stack, 'string');
    });

    })