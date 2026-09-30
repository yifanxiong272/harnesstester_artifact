let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.appendProgress - appends lines and notifies/render requests', function() {
        const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        // create a plain instance-like object that uses the prototype method
        const inst = Object.create(ToolCallComponent.prototype);
        inst.progressLines = ["existing"];
        inst.result = undefined;

        let rebuildCalled = false;
        let notifyCalled = false;
        let renderCalled = false;

        inst.rebuildBody = () => { rebuildCalled = true; };
        inst.notifySnapshotChange = () => { notifyCalled = true; };
        inst.ui = { requestRender: () => { renderCalled = true; } };

        // append multiple lines separated by newline
        inst.appendProgress("one\ntwo");

        assert.deepStrictEqual(inst.progressLines, ["existing", "one", "two"], "progressLines should have appended the new lines");
        assert.strictEqual(rebuildCalled, true, "rebuildBody should have been called");
        assert.strictEqual(notifyCalled, true, "notifySnapshotChange should have been called");
        assert.strictEqual(renderCalled, true, "ui.requestRender should have been called");
    });

    })