let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0006.WsConnection', function() {
        it('is exported and is a function', function() {
            const WsConnection = testpilot_subject &&
                                 testpilot_subject.file_0006 &&
                                 testpilot_subject.file_0006.WsConnection;
            assert.ok(WsConnection, 'WsConnection should be exported at testpilot_subject.file_0006.WsConnection');
            assert.equal(typeof WsConnection, 'function', 'WsConnection should be a function/constructor');
        });

            })
})