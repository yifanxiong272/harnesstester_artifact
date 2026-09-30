let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const WsConnection = testpilot_subject.file_0006 && testpilot_subject.file_0006.WsConnection;

    it('WsConnection.prototype.close should exist and be a function', function() {
        assert.ok(WsConnection, 'WsConnection constructor is missing');
        assert.strictEqual(typeof WsConnection.prototype.close, 'function', 'close is not a function');
    });

    })