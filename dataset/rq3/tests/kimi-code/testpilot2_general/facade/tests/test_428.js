let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.send - exists and is a function', function() {
        let WsConnection = testpilot_subject.file_0006.WsConnection;
        assert.strictEqual(typeof WsConnection.prototype.send, 'function');
    });

    })