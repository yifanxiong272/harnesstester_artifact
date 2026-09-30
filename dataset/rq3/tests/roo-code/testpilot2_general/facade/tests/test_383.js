let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.WorkspaceAPI.prototype.onDidCloseTextDocument', function() {
        it('forwards the listener to the underlying emitter.event and returns its result', function() {
            const proto = testpilot_subject.file_0009.WorkspaceAPI.prototype;
            const api = Object.create(proto);

            let receivedListener = null;
            const expectedReturn = { marker: 'returned' };

            // fake emitter with an event method that captures the listener and returns a sentinel
            api._onDidCloseTextDocument = {
                event: function(listener) {
                    receivedListener = listener;
                    return expectedReturn;
                }
            };

            function myListener() {}
            const ret = api.onDidCloseTextDocument(myListener);

            assert.strictEqual(ret, expectedReturn, 'should return whatever the underlying event method returns');
            assert.strictEqual(receivedListener, myListener, 'should pass the listener through to the underlying event method');
        });

            })
})