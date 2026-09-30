let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.WsConnection.prototype.onPong', function() {
    let WsConnection = testpilot_subject.file_0006 && testpilot_subject.file_0006.WsConnection;

    it('WsConnection.prototype.onPong should exist as a function', function() {
        assert.ok(WsConnection, 'WsConnection class is present');
        assert.strictEqual(typeof WsConnection.prototype.onPong, 'function');
    });

    })