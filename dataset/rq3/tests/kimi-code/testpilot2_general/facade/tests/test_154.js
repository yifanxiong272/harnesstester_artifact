let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ToolCallComponentProto = testpilot_subject.file_0003.ToolCallComponent.prototype;
    it('sets phase, endedAtMs, contextTokens, usage, summary and text; calls lifecycle hooks', function() {
        // Arrange: create a fake "this" that mimics the component instance
        const calls = {
            syncSubagentElapsedTimer: 0,
            rebuildContent: 0,
            notifySnapshotChange: 0,
            headerTextSet: []
        };
        const fakeThis = {
            // initial values
            subagentPhase: 'running',
            subagentEndedAtMs: undefined,
            subagentContextTokens: undefined,
            subagentUsage: undefined,
            subagentResultSummary: undefined,
            subagentText: '   ', // whitespace-only -> should be treated as empty and replaced
            // lifecycle stubs
            syncSubagentElapsedTimer() { calls.syncSubagentElapsedTimer++; },
            rebuildContent() { calls.rebuildContent++; },
            notifySnapshotChange() { calls.notifySnapshotChange++; },
            buildHeader() { return `PHASE:${this.subagentPhase}`; },
            headerText: {
                setText(txt) { calls.headerTextSet.push(txt); }
            },
            ui: {
                requestRender() { this._renderRequested = true; } // not asserted here
            }
        };

        const payload = {
            contextTokens: 5,
            usage: { tokens: 42 },
            resultSummary: 'the summary'
        };

        // Act
        const before = Date.now();
        ToolCallComponentProto.onSubagentCompleted.call(fakeThis, payload);
        const after = Date.now();

        // Assert
        assert.strictEqual(fakeThis.subagentPhase, 'done', 'subagentPhase should be set to done');
        assert.ok(typeof fakeThis.subagentEndedAtMs === 'number', 'subagentEndedAtMs should be a number');
        assert.ok(fakeThis.subagentEndedAtMs >= before && fakeThis.subagentEndedAtMs <= after,
            'subagentEndedAtMs should be set to now');
        assert.strictEqual(fakeThis.subagentContextTokens, 5, 'contextTokens should be copied when > 0');
        assert.deepStrictEqual(fakeThis.subagentUsage, payload.usage, 'usage should be copied');
        assert.strictEqual(fakeThis.subagentResultSummary, 'the summary', 'result summary should be stored');
        assert.strictEqual(fakeThis.subagentText, 'the summary', 'whitespace-only subagentText should be replaced by summary');
        // lifecycle hooks called
        assert.strictEqual(calls.syncSubagentElapsedTimer, 1, 'syncSubagentElapsedTimer called once');
        assert.strictEqual(calls.rebuildContent, 1, 'rebuildContent called once');
        assert.strictEqual(calls.notifySnapshotChange, 1, 'notifySnapshotChange called once');
        // header text updated using buildHeader (which observes the updated phase)
        assert.deepStrictEqual(calls.headerTextSet, ['PHASE:done'], 'headerText.setText should be called with buildHeader output');
    });

    })