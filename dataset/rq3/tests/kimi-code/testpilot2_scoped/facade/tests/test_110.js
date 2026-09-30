let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const archiveSession = testpilot_subject.file_0002.KimiCore.prototype.archiveSession;

    it('calls closeSession with an object containing sessionId and then calls sessionStore.archive with the sessionId (in order)', async function() {
        let callOrder = [];
        const mockThis = {
            closeSession: async function({sessionId}) {
                callOrder.push(['closeSession', sessionId]);
                return Promise.resolve('closed-' + sessionId);
            },
            sessionStore: {
                archive: async function(sessionId) {
                    callOrder.push(['archive', sessionId]);
                    return Promise.resolve('archived-' + sessionId);
                }
            }
        };

        const sessionId = 'session-123';
        const result = await archiveSession.call(mockThis, {sessionId});

        // function does not explicitly return a value, so result should be undefined
        assert.strictEqual(result, undefined);

        // Verify order and args
        assert.deepStrictEqual(callOrder, [
            ['closeSession', sessionId],
            ['archive', sessionId]
        ]);
    });

    })