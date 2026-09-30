let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.buildContent', function() {
    // Helper to create a lightweight instance that uses the real prototype but avoids constructor side-effects.
    function makeComponent(overrides = {}) {
        const Proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        const obj = Object.create(Proto);
        // sensible defaults used by buildContent
        obj.toolCall = { name: "DefaultTool", args: {} };
        obj.result = undefined;
        obj.expanded = false;
        obj._children = [];
        obj.addChild = function(child) { this._children.push(child); };
        // apply overrides
        for (const k of Object.keys(overrides)) obj[k] = overrides[k];
        return obj;
    }

    it('returns early when result is undefined (no-op)', function() {
        const comp = makeComponent({ result: undefined });
        // Should not throw and should return undefined
        const ret = comp.buildContent();
        assert.strictEqual(ret, undefined);
        assert.deepStrictEqual(comp._children, []);
    });

    })