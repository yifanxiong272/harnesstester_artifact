let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.setPlanInfo', function() {
    // Helper to create a ToolCallComponent-like object without calling unknown constructor
    function makeComponent(toolCallName, currentPlan, planPath) {
        // create object that uses the prototype under test so the method resolves correctly
        let comp = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
        comp.toolCall = { name: toolCallName };
        comp.currentPlan = currentPlan;
        comp.planPath = planPath;
        // counters to observe calls
        comp.rebuildCalls = 0;
        comp.renderCalls = 0;
        // stub out rebuildBody and ui.requestRender
        comp.rebuildBody = function() { this.rebuildCalls++; };
        comp.ui = {
            requestRender: function() { comp.renderCalls++; }
        };
        return comp;
    }

    it('does nothing when toolCall.name is not "ExitPlanMode"', function() {
        let c = makeComponent("NotExit", "planA", "pathA");
        // attempt to set different values, but name prevents any change
        c.setPlanInfo({ plan: "newPlan", path: "newPath" });
        assert.strictEqual(c.currentPlan, "planA", "currentPlan should remain unchanged");
        assert.strictEqual(c.planPath, "pathA", "planPath should remain unchanged");
        assert.strictEqual(c.rebuildCalls, 0, "rebuildBody should not be called");
        assert.strictEqual(c.renderCalls, 0, "requestRender should not be called");
    });

    })