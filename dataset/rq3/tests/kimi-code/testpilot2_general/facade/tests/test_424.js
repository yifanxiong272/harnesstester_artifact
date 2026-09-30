let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.onClose clears timers, calls handlers and logs info', function(done) {
        // Create a WsConnection-like object without invoking any real constructor
        const WsConnection = testpilot_subject.file_0006.WsConnection;
        let conn = Object.create(WsConnection.prototype);

        // initial state
        conn.closed = false;
        conn.id = 'conn-1';
        conn.gotClientHello = true;

        // ping interval should be cleared by onClose; schedule a repeated increment
        let pingCount = 0;
        conn.pingTimer = setInterval(() => {
            pingCount++;
        }, 20);

        // pong timeout should be cleared by onClose; schedule a one-shot flag
        let pongFired = false;
        conn.pongTimer = setTimeout(() => {
            pongFired = true;
        }, 60);

        // sessionClients.forgetConnection spy
        let forgetCalled = false;
        let forgetArg = null;
        conn.sessionClients = {
            forgetConnection: function(arg) {
                forgetCalled = true;
                forgetArg = arg;
            }
        };

        // subscriptions.clear spy
        let subsCleared = false;
        conn.subscriptions = {
            clear: function() { subsCleared = true; }
        };

        // handlers that should be called
        let fsCleanupCalled = false;
        let fsCleanupId = null;
        conn.fsWatchHandler = {
            cleanupConnection: function(id) {
                fsCleanupCalled = true;
                fsCleanupId = id;
            }
        };

        let termCleanupCalled = false;
        let termCleanupId = null;
        conn.terminalHandler = {
            cleanupConnection: function(id) {
                termCleanupCalled = true;
                termCleanupId = id;
            }
        };

        // logger spies
        let infoCalls = [];
        let warnCalls = [];
        conn.logger = {
            info: function(obj, msg) { infoCalls.push({obj: obj, msg: msg}); },
            warn: function(obj, msg) { warnCalls.push({obj: obj, msg: msg}); }
        };

        // Call the method under test
        conn.onClose(1000, "normal closure");

        // Wait long enough for the original timers to have fired if they weren't cleared.
        setTimeout(() => {
            try {
                // closed flag must be set
                assert.strictEqual(conn.closed, true, "conn.closed should be true after onClose");

                // timers should have been cleared: pingCount should remain 0 and pongFired false
                assert.strictEqual(pingCount, 0, "ping interval should have been cleared before it fired");
                assert.strictEqual(pongFired, false, "pong timeout should have been cleared and not fired");

                // sessionClients.forgetConnection and subscriptions.clear should have been called
                assert.strictEqual(forgetCalled, true, "sessionClients.forgetConnection should be called");
                assert.strictEqual(forgetArg, conn, "forgetConnection should be called with the connection object");
                assert.strictEqual(subsCleared, true, "subscriptions.clear should be called");

                // handlers should be invoked with the connection id
                assert.strictEqual(fsCleanupCalled, true, "fsWatchHandler.cleanupConnection should be called");
                assert.strictEqual(fsCleanupId, conn.id, "fsWatchHandler called with correct id");
                assert.strictEqual(termCleanupCalled, true, "terminalHandler.cleanupConnection should be called");
                assert.strictEqual(termCleanupId, conn.id, "terminalHandler called with correct id");

                // logger.info should have been called once with code, reason and gotClientHello
                assert.strictEqual(infoCalls.length, 1, "logger.info should be called once");
                let infoObj = infoCalls[0].obj;
                assert.strictEqual(infoObj.code, 1000);
                assert.strictEqual(infoObj.reason, "normal closure");
                assert.strictEqual(infoObj.gotClientHello, true);

                done();
            } catch (err) {
                done(err);
            } finally {
                // defensive cleanup: clear any timers that may still be present
                if (conn.pingTimer) clearInterval(conn.pingTimer);
                if (conn.pongTimer) clearTimeout(conn.pongTimer);
            }
        }, 120);
    });

    })