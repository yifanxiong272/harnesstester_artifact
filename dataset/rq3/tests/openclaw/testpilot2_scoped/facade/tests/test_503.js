let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const SafeOpenError = testpilot_subject.file_0018 && testpilot_subject.file_0018.SafeOpenError;

    it('constructor produces an Error-like object with code and message', function() {
        assert.ok(typeof SafeOpenError === 'function', 'SafeOpenError should be a constructor/function');

        const code = 404;
        const message = 'Not Found';
        const err = new SafeOpenError(code, message);

        // Should behave like an Error
        assert.ok(err instanceof Error, 'instance should be an Error');

        // message should match what we passed
        assert.strictEqual(err.message, message);

        // code should be available on the instance
        assert.strictEqual(err.code, code);
    });

    })