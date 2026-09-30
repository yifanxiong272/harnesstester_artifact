let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.logError with Error instance', function() {
        // create an object that has the method on its prototype without calling any constructor
        const mgr = Object.create(testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype);

        const logged = [];
        mgr.log = function(msg) { logged.push(msg); };

        const consoleErrCalls = [];
        const originalConsoleError = console.error;
        console.error = function(...args) { consoleErrCalls.push(args); };

        try {
            const err = new Error('boom');
            mgr.logError('prefix', err);

            const expected = 'prefix boom';
            assert.strictEqual(logged.length, 1, 'this.log should be called exactly once');
            assert.strictEqual(logged[0], expected, 'this.log should receive the composed message');

            assert.strictEqual(consoleErrCalls.length, 1, 'console.error should be called exactly once');
            // console.error may receive multiple args; our implementation passes a single string
            assert.strictEqual(consoleErrCalls[0][0], expected, 'console.error should receive the composed message');
        } finally {
            console.error = originalConsoleError;
        }
    });

    })