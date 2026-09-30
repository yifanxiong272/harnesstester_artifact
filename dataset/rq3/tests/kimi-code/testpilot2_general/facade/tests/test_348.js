let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Allow a little more time for asynchronous operations if needed
    this.timeout(5000);

    const WsConnProto = testpilot_subject &&
        testpilot_subject.file_0006 &&
        testpilot_subject.file_0006.WsConnection &&
        testpilot_subject.file_0006.WsConnection.prototype;

    it('onClientHello should exist and be a function', function() {
        assert.ok(WsConnProto, 'WsConnection prototype is present');
        assert.strictEqual(typeof WsConnProto.onClientHello, 'function',
            'onClientHello should be a function on the prototype');
    });

    })