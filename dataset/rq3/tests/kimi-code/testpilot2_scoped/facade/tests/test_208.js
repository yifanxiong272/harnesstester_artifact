let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.setModel', function() {
        it('calls reloadProviderManager and forwards payload (sessionId removed) and returns sync result', async function() {
            const KimiProto = testpilot_subject.file_0002.KimiCore.prototype;
            // Create an instance without running any constructor
            const instance = Object.create(KimiProto);

            let reloadCalled = 0;
            let seenSessionId = undefined;
            let seenPayload = undefined;

            instance.reloadProviderManager = function() {
                reloadCalled++;
            };

            instance.sessionApi = function(sessionId) {
                seenSessionId = sessionId;
                return {
                    setModel: function(payload) {
                        // return a synchronous value
                        seenPayload = payload;
                        return 'SYNC_RESULT';
                    }
                };
            };

            const result = await instance.setModel({ sessionId: 'session-123', alpha: 1, beta: 'x' });

            assert.strictEqual(reloadCalled, 1, 'reloadProviderManager should be called once');
            assert.strictEqual(seenSessionId, 'session-123', 'sessionApi should be called with the provided sessionId');
            assert.deepStrictEqual(seenPayload, { alpha: 1, beta: 'x' }, 'payload passed to sessionApi.setModel should exclude sessionId and include other properties');
            assert.strictEqual(result, 'SYNC_RESULT', 'setModel should return the value from sessionApi(sessionId).setModel');
        });

            })
})