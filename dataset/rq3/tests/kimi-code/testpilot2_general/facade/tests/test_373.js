let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const target = testpilot_subject &&
                   testpilot_subject.file_0006 &&
                   testpilot_subject.file_0006.WsConnection &&
                   testpilot_subject.file_0006.WsConnection.prototype &&
                   testpilot_subject.file_0006.WsConnection.prototype.onWatchFsRemove;

    it('test testpilot_subject.file_0006.WsConnection.prototype.onWatchFsRemove - is a function', function() {
        assert.ok(target, 'onWatchFsRemove should exist');
        assert.strictEqual(typeof target, 'function', 'onWatchFsRemove should be a function');
    });

    })