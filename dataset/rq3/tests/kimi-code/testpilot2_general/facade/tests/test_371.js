let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.onWatchFsAdd - no fsWatchHandler wired', function(done) {
        // Create an object using the prototype so we don't depend on constructor behavior.
        const proto = testpilot_subject.file_0006.WsConnection.prototype;
        const ws = Object.create(proto);
        ws.id = 'ws-1';
        let sent = null;
        ws.send = function(msg) {
            sent = msg;
            try {
                // We don't know the exact ack shape, stringify to look for expected pieces.
                const s = JSON.stringify(msg);
                assert(s.includes('fs watch handler not wired'), 'expected error string to be present in ack');
                // Ensure the original message id is referenced somewhere
                assert(s.includes(String(7)), 'expected message id to appear in ack');
                done();
            } catch (err) { done(err); }
        };
        // Call without wiring fsWatchHandler
        ws.onWatchFsAdd({ id: 7, payload: { session_id: 'sess1', paths: ['/x'] } });
    });

    })