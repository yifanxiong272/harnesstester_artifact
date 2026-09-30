let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0006.WsConnection.prototype.subscribe', function() {
    it('adds sid to subscriptions and calls sessionClients.subscribe when sid not present', function() {
      const WsProto = testpilot_subject.file_0006.WsConnection.prototype;
      // create instance without invoking constructor to keep test self-contained
      const ws = Object.create(WsProto);
      ws.subscriptions = new Set();
      let called = 0;
      let receivedConn = null;
      let receivedSid = null;
      ws.sessionClients = {
        subscribe: function(conn, sid) {
          called++;
          receivedConn = conn;
          receivedSid = sid;
        }
      };

      ws.subscribe('room1');

      assert.strictEqual(ws.subscriptions.has('room1'), true, 'subscription should be added');
      assert.strictEqual(called, 1, 'sessionClients.subscribe should be called once');
      assert.strictEqual(receivedConn, ws, 'first arg to sessionClients.subscribe should be the connection instance');
      assert.strictEqual(receivedSid, 'room1', 'second arg to sessionClients.subscribe should be the sid');
    });

        })
})