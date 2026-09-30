let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('forwards listener to _onDidChangeWorkspaceFolders.event and returns its result', function() {
        const proto = testpilot_subject.file_0009.WorkspaceAPI.prototype;
        // Create a plain object that uses the real prototype but has a custom _onDidChangeWorkspaceFolders
        const obj = Object.create(proto);

        let receivedListener = null;
        obj._onDidChangeWorkspaceFolders = {
            event: function(listener) {
                receivedListener = listener;
                return { forwarded: true };
            }
        };

        const listener = function() { /* noop */ };
        const result = proto.onDidChangeWorkspaceFolders.call(obj, listener);

        assert.strictEqual(receivedListener, listener, 'the listener should be forwarded to event()');
        assert.deepStrictEqual(result, { forwarded: true }, 'the return value from event() should be returned unchanged');
    });

    })