let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.setThinking', function() {
        it('forwards sessionId to sessionApi and forwards payload without sessionId to setThinking (sync return)', function() {
            // create an object that uses the real prototype but without running any constructor
            let proto = testpilot_subject.file_0002.KimiCore.prototype;
            let instance = Object.create(proto);

            let seenSessionId;
            let seenPayload;
            // stub sessionApi to capture the sessionId and payload and return a sync value
            instance.sessionApi = function(sessionId) {
                seenSessionId = sessionId;
                return {
                    setThinking: function(payload) {
                        seenPayload = payload;
                        return 'SYNC_OK';
                    }
                };
            };

            // call the method under test
            let result = instance.setThinking({ sessionId: 'SESSION-123', thought: true, count: 5 });

            // assertions
            assert.strictEqual(seenSessionId, 'SESSION-123', 'sessionApi should be called with provided sessionId');
            assert.deepStrictEqual(seenPayload, { thought: true, count: 5 }, 'setThinking should be called with payload without sessionId');
            assert.strictEqual(result, 'SYNC_OK', 'should return value returned by setThinking');
        });

            })
})