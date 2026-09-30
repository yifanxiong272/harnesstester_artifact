let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('messagesToTurns: empty messages returns an array (empty)', function(done) {
        let messages = [];
        // make approvals an iterable (Map) to match the function's expectations
        let approvals = new Map();
        // a getFileUrl that would throw if called (ensures function doesn't call it for empty messages)
        let getFileUrl = function() { throw new Error('getFileUrl should not be called'); };

        let result = testpilot_subject.file_0005.messagesToTurns(messages, approvals, getFileUrl);
        assert.ok(Array.isArray(result), 'result should be an array');
        assert.strictEqual(result.length, 0, 'result array should be empty for empty messages');
        done();
    });

    })