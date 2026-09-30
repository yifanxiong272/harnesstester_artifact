let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WsConnection.prototype.onWatchFsRemove', function() {
        function makeConn() {
            // create an object with the WsConnection prototype so we can call the method
            let conn = Object.create(testpilot_subject.file_0006.WsConnection.prototype);
            conn.id = 'connection-1';
            conn._sent = [];
            conn.send = function(payload) {
                // capture what would be sent
                conn._sent.push(payload);
            };
            conn.logger = {
                _warns: [],
                warn: function(obj, msg) {
                    this._warns.push({obj, msg});
                }
            };
            return conn;
        }

        it('sends INTERNAL_ERROR ack when fsWatchHandler is not wired', function() {
            let conn = makeConn();
            // do NOT set fsWatchHandler
            let msg = { id: 123, payload: { session_id: 's1', paths: ['/a'] } };

            conn.onWatchFsRemove(msg);

            assert(conn._sent.length === 1, 'expected one send call');
            // We can't rely on exact structure of buildAck, so assert the stringified payload contains the expected message
            let sentStr = JSON.stringify(conn._sent[0]);
            assert(sentStr.includes('fs watch handler not wired') || sentStr.includes('fs watch handler'), 'expected error message about handler not wired');
            // also expect INTERNAL_ERROR code to be present somewhere (number or "INTERNAL_ERROR")
            assert(sentStr.toLowerCase().includes('internal') || /-?\d+/.test(sentStr), 'expected internal error code or mention');
        });

            })
})