let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // convenience reference to the function under test
    const resolvePermissionRequest = testpilot_subject.file_0016.resolvePermissionRequest;

    it('should cancel when there are no options (prompt not called)', async function() {
        let logs = [];
        let promptCalls = [];
        const deps = {
            log: (line) => logs.push(line),
            prompt: async (toolName, toolTitle) => { promptCalls.push({toolName, toolTitle}); return true; },
            cwd: '/tmp'
        };

        const params = { options: [] };

        const result = await resolvePermissionRequest(params, deps);

        // Behaviour expectations:
        // - prompt must not have been called when there are no options
        assert.strictEqual(promptCalls.length, 0, 'prompt should not be called when no options');
        // - a cancellation log line should have been emitted
        assert.ok(logs.some(l => l.includes('[permission cancelled]')), 'should log cancellation');
        // - result should be a (non-null) value (function returns a value indicating cancellation)
        assert.ok(result !== undefined && result !== null, 'should return a cancellation value');
    });

    })