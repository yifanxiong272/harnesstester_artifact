let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.onAbort - is a function with arity 1', function(done) {
        let onAbort = testpilot_subject.file_0006.WsConnection.prototype.onAbort;
        assert.strictEqual(typeof onAbort, 'function', 'onAbort should be a function');
        // Expect one argument (the message)
        assert.ok(onAbort.length >= 1, 'onAbort should accept at least one parameter');
        done();
    });

    })