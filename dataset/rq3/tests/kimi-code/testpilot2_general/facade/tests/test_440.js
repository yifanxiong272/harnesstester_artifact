let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0008.reduceAppEvent', function() {
    const reduceAppEvent = testpilot_subject.file_0008.reduceAppEvent;

    function baseState() {
        return {
            sessions: [],
            messagesBySession: {},
            tasksBySession: {},
            goalBySession: {},
            approvalsBySession: {},
            questionsBySession: {},
            lastSeqBySession: {},
            compactionBySession: {},
            warnings: [],
            config: {},
            activeSessionId: undefined,
            // any other maps the reducer may touch
        };
    }

    it('adds a session on sessionCreated (no duplicate)', function() {
        const state = baseState();
        const session = { id: 's1', title: 'First', updatedAt: '2020-01-01T00:00:00Z' };

        const event = { type: 'sessionCreated', session };
        const meta = { sessionId: 's1', seq: 1 };

        const next = reduceAppEvent(state, event, meta);
        assert.strictEqual(next.sessions.length, 1);
        assert.strictEqual(next.sessions[0].id, 's1');

        // Creating same session again should not duplicate
        const next2 = reduceAppEvent(next, event, { sessionId: 's1', seq: 2 });
        assert.strictEqual(next2.sessions.length, 1, 'duplicate session was not prevented');
    });

    })