let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports WsConnection constructor', function() {
        assert.ok(testpilot_subject, 'module should exist');
        assert.ok(testpilot_subject.file_0006, 'file_0006 should exist on module');
        assert.ok(testpilot_subject.file_0006.WsConnection, 'WsConnection should exist');
        assert.strictEqual(typeof testpilot_subject.file_0006.WsConnection, 'function', 'WsConnection should be a constructor');
    });

    })