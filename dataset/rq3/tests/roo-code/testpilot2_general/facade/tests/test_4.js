let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype;
    const log = proto.log;

    it('calls this.logFn with the message when logFn is present and does not call console.log', function() {
        let received;
        let consoleCalled = false;

        // stub console.log to detect any unexpected calls
        const originalConsoleLog = console.log;
        console.log = function() { consoleCalled = true; };

        try {
            const ctx = {
                logFn: function(msg) { received = msg; }
            };

            const message = "test-message";
            const ret = log.call(ctx, message);

            // function should return undefined
            assert.strictEqual(ret, undefined);

            // logFn should have been called with the message
            assert.strictEqual(received, message);

            // console.log must not have been called because logFn exists
            assert.strictEqual(consoleCalled, false);
        } finally {
            // restore console.log
            console.log = originalConsoleLog;
        }
    });

    })