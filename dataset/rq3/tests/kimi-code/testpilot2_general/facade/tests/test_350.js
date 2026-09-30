let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0006.WsConnection.prototype.syncSessions', function() {
    // Grab the function under test (if present). Tests will fail clearly if it's absent.
    const syncFn = testpilot_subject &&
                   testpilot_subject.file_0006 &&
                   testpilot_subject.file_0006.WsConnection &&
                   testpilot_subject.file_0006.WsConnection.prototype &&
                   testpilot_subject.file_0006.WsConnection.prototype.syncSessions;

    it('should exist and be an async function', function() {
        assert.ok(syncFn, 'syncSessions function not found on prototype');
        // Async functions have constructor name "AsyncFunction"
        assert.strictEqual(syncFn.constructor.name, 'AsyncFunction', 'syncSessions is expected to be an async function');
    });

    })