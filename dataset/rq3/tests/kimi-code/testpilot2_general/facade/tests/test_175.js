let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const append = testpilot_subject.file_0003.ToolCallComponent.prototype.appendSubagentText;

    it('appends text (default kind) to subagentText and triggers lifecycle methods', function(done) {
        // Prepare a context object that mimics the component instance
        const ctx = {
            subagentThinkingText: "",
            subagentText: "",
            subagentPhase: undefined,
            headerText: {
                lastSet: null,
                setText: function(txt) { this.lastSet = txt; }
            },
            buildHeader: function() { return "HDR|" + this.subagentText + "|" + this.subagentThinkingText; },
            rebuildContent: function() { this.rebuilt = (this.rebuilt || 0) + 1; },
            notifySnapshotChange: function() { this.notified = (this.notified || 0) + 1; },
            ui: {
                rendered: false,
                requestRender: function() { this.rendered = true; }
            }
        };

        // Call the method (default kind should be "text")
        append.call(ctx, "hello");

        // Assertions
        assert.strictEqual(ctx.subagentText, "hello", "subagentText should have the appended text");
        assert.strictEqual(ctx.subagentThinkingText, "", "subagentThinkingText should remain unchanged");
        assert.strictEqual(ctx.subagentPhase, "running", "subagentPhase should be set to running when previously undefined");
        assert.strictEqual(ctx.headerText.lastSet, "HDR|hello|", "headerText.setText should be called with buildHeader() result");
        assert.strictEqual(ctx.rebuilt, 1, "rebuildContent should be called once");
        assert.strictEqual(ctx.notified, 1, "notifySnapshotChange should be called once");
        assert.strictEqual(ctx.ui.rendered, true, "ui.requestRender should be called");

        done();
    });

    })