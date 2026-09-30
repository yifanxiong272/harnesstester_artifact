let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const closeSession = testpilot_subject.file_0002.KimiCore.prototype.closeSession;

    it('removes session after successful close (async)', async function() {
        const sessions = new Map();
        let closedCalled = false;
        sessions.set('s1', {
            close: async function() {
                // simulate async work
                await new Promise(resolve => setTimeout(resolve, 10));
                closedCalled = true;
            }
        });

        // call method with a plain object that has the sessions Map
        await closeSession.call({ sessions }, { sessionId: 's1' });

        assert.strictEqual(closedCalled, true, 'session.close should have been called');
        assert.strictEqual(sessions.has('s1'), false, 'session should be removed from the map after close');
    });

    })