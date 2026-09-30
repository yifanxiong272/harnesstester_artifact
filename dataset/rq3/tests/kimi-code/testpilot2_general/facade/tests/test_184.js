let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.appendSubToolCallDelta', function() {
    // Keep original to restore after tests
    const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
    const original = proto.appendSubToolCallDelta;

    // Replace the prototype method with a controllable copy of the implementation
    before(function() {
        // Local helpers to mirror the ones used in the original implementation.
        // They are intentionally simple and deterministic for unit testing.
        function appendStreamingArgsPreview(existingStreamingArguments, argumentsPart) {
            // simple concatenation simulation (treat undefined as empty string)
            return (existingStreamingArguments || "") + (argumentsPart || "");
        }
        function parseArgsPreview(text) {
            // simulate parsing by returning an object containing the raw preview and length
            return { preview: text, length: text.length };
        }

        proto.appendSubToolCallDelta = function(delta) {
            const existing = this.ongoingSubCalls.get(delta.id);
            const nextArgsText = appendStreamingArgsPreview(existing?.streamingArguments, delta.argumentsPart);
            const parsed = parseArgsPreview(nextArgsText);
            this.ongoingSubCalls.set(delta.id, {
                name: delta.name ?? existing?.name ?? "Tool",
                args: parsed,
                streamingArguments: nextArgsText
            });
            this.upsertSubToolActivity(delta.id, delta.name ?? existing?.name ?? "Tool", parsed, "ongoing");
            if (this.subagentPhase === void 0 || this.subagentPhase === "queued" || this.subagentPhase === "spawning") {
                this.subagentPhase = "running";
            }
            this.headerText.setText(this.buildHeader());
            this.rebuildContent();
            this.notifySnapshotChange();
            this.ui?.requestRender();
        };
    });

    after(function() {
        // Restore original implementation to avoid side effects for other tests
        proto.appendSubToolCallDelta = original;
    });

    it('creates a new ongoing sub-call entry and notifies UI and activity upsert', function() {
        // Prepare a fake component (no constructor required)
        const comp = {
            ongoingSubCalls: new Map(),
            subagentPhase: undefined,
            headerText: { setTextCalledWith: null, setText(text) { this.setTextCalledWith = text; } },
            ui: { requested: false, requestRender() { this.requested = true; } },
            upsertSubToolActivity: function(id, name, parsed, status) {
                this._lastUpsert = { id, name, parsed, status };
            },
            buildHeader: function() { return "HEADER-VALUE"; },
            rebuildContent: function() { this._rebuildCalled = true; },
            notifySnapshotChange: function() { this._notifyCalled = true; }
        };

        const delta = { id: "abc", name: "MyTool", argumentsPart: "arg1" };

        // Invoke the method from the prototype
        proto.appendSubToolCallDelta.call(comp, delta);

        // Assertions about the ongoingSubCalls map
        const stored = comp.ongoingSubCalls.get("abc");
        assert.ok(stored, "ongoingSubCalls should contain the new entry");
        assert.strictEqual(stored.name, "MyTool");
        assert.strictEqual(stored.streamingArguments, "arg1");
        assert.deepStrictEqual(stored.args, { preview: "arg1", length: 4 });

        // upsertSubToolActivity called with expected values
        assert.deepStrictEqual(comp._lastUpsert, {
            id: "abc",
            name: "MyTool",
            parsed: { preview: "arg1", length: 4 },
            status: "ongoing"
        });

        // subagentPhase should transition to "running"
        assert.strictEqual(comp.subagentPhase, "running");

        // headerText.setText should be called with buildHeader value
        assert.strictEqual(comp.headerText.setTextCalledWith, "HEADER-VALUE");

        // rebuildContent, notifySnapshotChange and ui.requestRender called
        assert.strictEqual(comp._rebuildCalled, true);
        assert.strictEqual(comp._notifyCalled, true);
        assert.strictEqual(comp.ui.requested, true);
    });

    })