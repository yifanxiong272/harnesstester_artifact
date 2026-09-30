let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0003.ToolCallComponent.prototype.setBackgroundTaskTerminalStatus;

    it('sets phase to "done" for completed and calls lifecycle hooks', function() {
        // Arrange
        let syncCalled = false;
        let rebuildCalled = false;
        let notifyCalled = false;
        let headerTextArg = null;
        const obj = {
            backgroundTaskTerminalPhase: undefined,
            subagentError: undefined,
            subagentEndedAtMs: undefined,
            syncSubagentElapsedTimer() { syncCalled = true; },
            rebuildContent() { rebuildCalled = true; },
            notifySnapshotChange() { notifyCalled = true; },
            headerText: { setText(t) { headerTextArg = t; } },
            buildHeader() { return 'HEADER_TEXT'; }
        };

        const before = Date.now();
        // Act
        fn.call(obj, "completed", {});

        // Assert
        assert.strictEqual(obj.backgroundTaskTerminalPhase, "done");
        assert.ok(typeof obj.subagentEndedAtMs === 'number');
        assert.ok(obj.subagentEndedAtMs >= before);
        assert.strictEqual(syncCalled, true, "syncSubagentElapsedTimer should be called");
        assert.strictEqual(rebuildCalled, true, "rebuildContent should be called");
        assert.strictEqual(notifyCalled, true, "notifySnapshotChange should be called");
        assert.strictEqual(headerTextArg, 'HEADER_TEXT', "headerText.setText should be called with buildHeader()");
    });

    })