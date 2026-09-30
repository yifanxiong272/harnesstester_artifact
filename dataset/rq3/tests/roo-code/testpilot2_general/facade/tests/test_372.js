let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidChangeTextDocument', function() {

        it('returns exactly what _onDidChangeTextDocument.event returns', function() {
            // Create an object that uses the prototype without running the constructor,
            // avoiding any constructor-side path operations that expect strings.
            const ws = Object.create(testpilot_subject.file_0009.WorkspaceAPI.prototype);

            // Prepare a sentinel disposable object that the mock event will return
            const sentinelDisposable = { disposed: false, dispose: function(){ this.disposed = true; } };

            // Replace the internal emitter with a mock that records invocation and returns our sentinel
            let eventCalled = false;
            ws._onDidChangeTextDocument = {
                event: function(listener) {
                    eventCalled = true;
                    // We don't need to call the listener here; just return the sentinel
                    return sentinelDisposable;
                }
            };

            const returned = ws.onDidChangeTextDocument(function () {});
            assert.strictEqual(eventCalled, true, '_onDidChangeTextDocument.event should have been called');
            assert.strictEqual(returned, sentinelDisposable, 'onDidChangeTextDocument should return the value from the underlying event');
        });

    })
})