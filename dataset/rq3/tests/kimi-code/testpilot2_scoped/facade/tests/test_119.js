let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const reloadSessionFn = testpilot_subject.file_0002.KimiCore.prototype.reloadSession;

    // Helper to create a fake KimiCore "this" with injectable behavior
    function makeCoreFake(opts = {}) {
        const calls = {
            reloadProviderManager: 0,
            clearRuntimeCache: 0,
            reloadPluginsArgs: [],
            resumeSessionArgs: [],
        };

        // minimal sessions-like object with spyable methods
        const sessions = {
            map: {},
            deletedKeys: [],
            get(key) { return this.map[key]; },
            set(key, value) { this.map[key] = value; },
            delete(key) { this.deletedKeys.push(key); delete this.map[key]; },
        };

        const sessionStore = {
            async get(id) {
                // allow override by opts.sessionSummary or by id
                return opts.sessionSummary || { id: id || 'default-session' };
            }
        };

        const fake = {
            // injected dependencies / spies
            sessionStore,
            sessions,
            reloadProviderManager() { calls.reloadProviderManager++; },
            clearRuntimeCache() { calls.clearRuntimeCache++; },
            async reloadPlugins(args) { calls.reloadPluginsArgs.push(args); return opts.reloadPluginsResult; },
            async resumeSession(args) { calls.resumeSessionArgs.push(args); return opts.resumeResult; },
            // expose call records for assertions
            __calls: calls
        };

        return fake;
    }

    it('throws KimiError when an active turn is running', async function() {
        const core = makeCoreFake({ sessionSummary: { id: 's1' } });

        // active session that has an active turn
        core.sessions.set('s1', { hasActiveTurn: true, closeForReload: async () => { throw new Error('should not be called'); } });

        // call reloadSession (using function from prototype with our fake this)
        try {
            await reloadSessionFn.call(core, { sessionId: 's1' });
            // if we get here, the test should fail
            assert.fail('Expected reloadSession to throw when hasActiveTurn === true');
        } catch (err) {
            // The implementation throws a KimiError with message containing the session id and reason.
            assert(err instanceof Error, 'Thrown value should be an Error');
            assert(err.message.includes('cannot be reloaded while a turn is running') || err.message.includes('cannot be reloaded'), 'Error message should indicate turn is running');
            assert(err.message.includes('s1'), 'Error message should include session id');
        }
    });

    })