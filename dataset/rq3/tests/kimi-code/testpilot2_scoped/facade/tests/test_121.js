let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the forkSession function from the prototype so we can call it with a mocked "this".
    const KimiCore = testpilot_subject.file_0002.KimiCore;
    const forkSession = KimiCore.prototype.forkSession;

    it('throws if the source session has an active turn', async function() {
        // Arrange
        const sourceSessionId = 'source-1';
        const targetSessionId = 'target-1';

        const fakeThis = {
            // sessionStore.get should return an object with id
            sessionStore: {
                get: async (sessionId) => {
                    assert.strictEqual(sessionId, sourceSessionId);
                    return { id: sourceSessionId };
                },
                // fork should not be reached in this scenario, but provide a stub
                fork: async () => { throw new Error('fork should not be called when active turn exists'); }
            },
            // sessions map contains an active session with hasActiveTurn === true
            sessions: new Map([[sourceSessionId, { hasActiveTurn: true }]]),
            // resumeSession should also not be reached
            resumeSession: async () => { throw new Error('resumeSession should not be called when active turn exists'); }
        };

        // Act / Assert
        // Expect the call to reject with an error that indicates the session cannot be forked while a turn is running
        await assert.rejects(
            () => forkSession.call(fakeThis, { sessionId: sourceSessionId, id: targetSessionId }),
            (err) => {
                // Basic checks on the thrown error: message should mention "cannot be forked while a turn is running"
                // and should mention the session id.
                const msg = String(err && err.message);
                return msg.includes('cannot be forked while a turn is running') && msg.includes(sourceSessionId);
            },
            'Expected a KimiError about active turn preventing fork'
        );
    });

    })