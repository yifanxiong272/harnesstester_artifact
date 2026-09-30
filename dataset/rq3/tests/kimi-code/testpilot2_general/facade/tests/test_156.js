let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const updateFn = testpilot_subject.file_0003.ToolCallComponent.prototype.updateSubagentMetrics;

    it('updates subagentContextTokens and subagentUsage when provided and calls lifecycle/UI methods', function() {
        // Arrange: create a lightweight "this" object that has the methods/properties the function expects.
        let ctx = {
            subagentContextTokens: 0,
            subagentUsage: { initial: true },

            // buildHeader should be called and its return value passed to headerText.setText
            buildHeaderCalled: false,
            buildHeader() {
                this.buildHeaderCalled = true;
                return 'HEADER-STRING';
            },

            headerText: {
                lastSetText: null,
                setText(text) { this.lastSetText = text; }
            },

            invalidateCalled: 0,
            invalidate() { this.invalidateCalled += 1; },

            notifySnapshotChangeCalled: 0,
            notifySnapshotChange() { this.notifySnapshotChangeCalled += 1; },

            ui: {
                requestRenderCalled: 0,
                requestRender() { this.requestRenderCalled += 1; }
            }
        };

        // Act: payload with contextTokens > 0 and usage provided
        const payload = { contextTokens: 123, usage: { tokens: 123 } };
        updateFn.call(ctx, payload);

        // Assert: properties updated
        assert.strictEqual(ctx.subagentContextTokens, 123, 'subagentContextTokens should be updated to payload.contextTokens');
        assert.deepStrictEqual(ctx.subagentUsage, payload.usage, 'subagentUsage should be updated to payload.usage');

        // buildHeader and headerText.setText called with returned string
        assert.ok(ctx.buildHeaderCalled, 'buildHeader should have been called');
        assert.strictEqual(ctx.headerText.lastSetText, 'HEADER-STRING', 'headerText.setText should receive buildHeader output');

        // lifecycle methods called
        assert.strictEqual(ctx.invalidateCalled, 1, 'invalidate should be called once');
        assert.strictEqual(ctx.notifySnapshotChangeCalled, 1, 'notifySnapshotChange should be called once');

        // ui.requestRender called once
        assert.strictEqual(ctx.ui.requestRenderCalled, 1, 'ui.requestRender should be called once');
    });

    })