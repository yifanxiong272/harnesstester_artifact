let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const func = testpilot_subject.file_0003.ToolCallComponent.prototype.onSubagentFailed;
    if (typeof func !== 'function') {
        throw new Error('Expected onSubagentFailed to be a function on the prototype');
    }

    const originalDateNow = Date.now;

    afterEach(function() {
        // Restore Date.now in case any test mocked it
        Date.now = originalDateNow;
    });

    it('sets subagentPhase to "failed", sets subagentEndedAtMs when missing, sets subagentError, and calls lifecycle methods including ui.requestRender', function() {
        // Freeze time
        const fixedNow = 1600000000000;
        Date.now = () => fixedNow;

        // Prepare spies / flags to observe calls
        let syncCalled = false;
        let rebuildCalled = false;
        let notifyCalled = false;
        let headerTextSetArg = undefined;
        let uiRequested = false;

        // Context object to use as `this`
        const ctx = {
            subagentPhase: 'running',
            // subagentEndedAtMs undefined to trigger assignment
            buildHeader: function() {
                // return something that depends on state so we can verify order
                return 'HEADER:' + this.subagentPhase;
            },
            headerText: {
                setText: function(text) {
                    headerTextSetArg = text;
                }
            },
            syncSubagentElapsedTimer: function() { syncCalled = true; },
            rebuildContent: function() { rebuildCalled = true; },
            notifySnapshotChange: function() { notifyCalled = true; },
            ui: {
                requestRender: function() { uiRequested = true; }
            }
        };

        const payload = { error: new Error('subagent failed') };

        // Call the function
        func.call(ctx, payload);

        // Assertions
        assert.strictEqual(ctx.subagentPhase, 'failed', 'phase should be "failed"');
        assert.strictEqual(ctx.subagentEndedAtMs, fixedNow, 'subagentEndedAtMs should be set to Date.now() when missing');
        assert.strictEqual(ctx.subagentError, payload.error, 'subagentError should be set from payload');
        assert.strictEqual(syncCalled, true, 'syncSubagentElapsedTimer should be called');
        assert.strictEqual(rebuildCalled, true, 'rebuildContent should be called');
        assert.strictEqual(notifyCalled, true, 'notifySnapshotChange should be called');
        assert.strictEqual(headerTextSetArg, 'HEADER:failed', 'headerText.setText should be called with buildHeader() result');
        assert.strictEqual(uiRequested, true, 'ui.requestRender should be called when ui exists');
    });

    })