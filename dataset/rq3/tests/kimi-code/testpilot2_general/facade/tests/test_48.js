let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent', function() {
    const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;

    // Provide a minimal ui stub to satisfy calls to ui.requestRender()
    const uiStub = { requestRender: () => {} };

    afterEach(function() {
        // No global cleanup required here; individual tests will dispose instances they create.
    });

    it('buildHeader includes tool name and getReadSnapshot returns pending when no result', function() {
        const toolCall = {
            id: 't1',
            name: 'Echo',
            args: {},
            truncated: false
        };
        const c = new ToolCallComponent(toolCall, undefined, uiStub, '/workspace');
        try {
            const header = c.buildHeader();
            // header is styled; just assert the tool name appears somewhere in it
            assert.ok(typeof header === 'string' && header.indexOf('Echo') !== -1, 'header should contain tool name');

            const snapshot = c.getReadSnapshot();
            assert.strictEqual(snapshot.toolCallId, 't1');
            assert.strictEqual(snapshot.phase, 'pending');
            assert.strictEqual(snapshot.lines, 0);
        } finally {
            c.dispose();
        }
    });

    })