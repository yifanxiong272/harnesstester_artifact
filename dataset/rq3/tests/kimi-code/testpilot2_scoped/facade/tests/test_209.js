let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const setModel = testpilot_subject.file_0002.KimiCore.prototype.setModel;

    it('calls reloadProviderManager and forwards payload without sessionId to sessionApi(sessionId).setModel', async function() {
        // Arrange: fake "this" with spies and a sessionApi that resolves with the received args
        let reloadCalled = false;
        let receivedSessionId = undefined;
        let receivedPayload = undefined;

        const fakeThis = {
            reloadProviderManager: () => { reloadCalled = true; },
            sessionApi: (sessionId) => {
                receivedSessionId = sessionId;
                return {
                    setModel: (payload) => {
                        receivedPayload = payload;
                        return Promise.resolve({ ok: true, sessionIdReceived: sessionId, payloadReceived: payload });
                    }
                };
            }
        };

        const input = { sessionId: 'sess-123', model: 'gpt-test', settings: { temp: 0.3 } };

        // Act
        const result = await setModel.call(fakeThis, input);

        // Assert
        assert.strictEqual(reloadCalled, true, 'reloadProviderManager should have been called');
        assert.strictEqual(receivedSessionId, 'sess-123', 'sessionApi should be called with the provided sessionId');
        assert.deepStrictEqual(receivedPayload, { model: 'gpt-test', settings: { temp: 0.3 } }, 'payload passed to setModel should exclude sessionId');
        assert.deepStrictEqual(result, { ok: true, sessionIdReceived: 'sess-123', payloadReceived: receivedPayload }, 'returned value should come from sessionApi(...).setModel');
    });

    })