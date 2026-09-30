let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidOpenTextDocument', function() {
        it('forwards the listener to this._onDidOpenTextDocument.event and returns its value', function() {
            // grab the prototype function
            const fn = testpilot_subject.file_0009.WorkspaceAPI.prototype.onDidOpenTextDocument;

            // prepare a fake this with a spyable _onDidOpenTextDocument.event
            let receivedListener = null;
            const returnedObject = { disposed: false };
            const fakeThis = {
                _onDidOpenTextDocument: {
                    event: function(listener) {
                        receivedListener = listener;
                        return returnedObject;
                    }
                }
            };

            // create a sample listener
            function sampleListener(doc) { /* no-op */ }

            // call the method and assert behavior
            const res = fn.call(fakeThis, sampleListener);
            assert.strictEqual(receivedListener, sampleListener, 'listener was forwarded to event');
            assert.strictEqual(res, returnedObject, 'return value is the value returned by event');
        });

            })
})