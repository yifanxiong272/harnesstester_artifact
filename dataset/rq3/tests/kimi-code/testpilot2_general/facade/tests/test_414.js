let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Give a little extra time for timers to run in CI
    this.timeout(5000);

    it('startPingTimer sends a ping and clears any existing pong timer', function(done) {
        const startPingTimer = testpilot_subject.file_0006.WsConnection.prototype.startPingTimer;

        // Spy for send
        let sendCalls = [];
        const fakeSend = (payload) => {
            sendCalls.push(payload);
        };

        // Track clearTimeout calls by monkeypatching global.clearTimeout temporarily
        const origClearTimeout = global.clearTimeout;
        let clearTimeoutCalled = false;
        global.clearTimeout = function(t) {
            clearTimeoutCalled = true;
            return origClearTimeout(t);
        };

        // Fake "existing" pong timer id (a number or object - doesn't matter to clearTimeout)
        let existingPongTimer = 12345;

        // Minimal fake "this" for the method
        const fakeThis = {
            closed: false,
            send: fakeSend,
            logger: { warn: () => {} },
            socket: { terminate: () => {} },
            pongTimer: existingPongTimer,
            pongTimeoutMs: 50,
            pingIntervalMs: 20,
            pingTimer: null
        };

        // Call the method using our fake 'this'
        startPingTimer.call(fakeThis);

        // Wait enough for at least one ping to be sent and for the function to have attempted to clear existing pongTimer
        setTimeout(() => {
            try {
                // send should have been called at least once
                assert(sendCalls.length >= 1, 'expected send to be called at least once');

                // clearTimeout should have been called to clear the existing pongTimer
                assert.strictEqual(clearTimeoutCalled, true, 'expected clearTimeout to be called to clear existing pong timer');

                // The method should have stored a new pongTimer (not equal to the original sentinel)
                assert(fakeThis.pongTimer !== existingPongTimer, 'expected pongTimer to be replaced');

                // cleanup timers
                if (fakeThis.pingTimer) clearInterval(fakeThis.pingTimer);
                if (fakeThis.pongTimer) clearTimeout(fakeThis.pongTimer);

                // restore clearTimeout
                global.clearTimeout = origClearTimeout;

                done();
            } catch (err) {
                // Restore before failing
                if (fakeThis.pingTimer) clearInterval(fakeThis.pingTimer);
                if (fakeThis.pongTimer) clearTimeout(fakeThis.pongTimer);
                global.clearTimeout = origClearTimeout;
                done(err);
            }
        }, 120);
    });

    })