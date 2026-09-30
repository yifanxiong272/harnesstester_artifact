let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const countForConnection = testpilot_subject.file_0001.FsWatcherService.prototype.countForConnection;

    it('returns 0 when the connectionId is not present', function() {
        const ctx = { connections: new Map() };
        assert.strictEqual(countForConnection.call(ctx, 'missing'), 0);
    });

    })