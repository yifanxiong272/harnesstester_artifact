let mocha = require('mocha');
let assert = require('assert');

// We create a mock of the module and the surrounding helpers that the method expects.
// This keeps the tests self-contained and avoids relying on external resources.
let testpilot_subject = { file_0003: {} };

// Helper functions / objects that the method references.
let lastColorArg = null;
let import_theme = {
    currentTheme: {
        color: function(name) {
            lastColorArg = name;
            return "#COLOR_FOR_" + name;
        }
    }
};

// These will be overridden inside individual tests as needed.
let isExitPlanModeOutcomeOutput = function(o) { return false; };
let interpretExitPlanModeOutcome = function(o) { return { kind: "unknown" }; };

// Define the ToolCallComponent and attach the method under test.
// The function body is taken exactly from the prompt, but it will close over the
// helper variables defined above (isExitPlanModeOutcomeOutput, interpretExitPlanModeOutcome, import_theme).
testpilot_subject.file_0003.ToolCallComponent = function() {
    // allow constructing with initial properties
};
testpilot_subject.file_0003.ToolCallComponent.prototype.resolvePlanBoxStatus = function() {
    const result = this.result;
    if (this.toolCall.name !== "ExitPlanMode" || result === void 0) return void 0;
    if (!isExitPlanModeOutcomeOutput(result.output)) return void 0;
    const outcome = interpretExitPlanModeOutcome(result.output);
    if (outcome.kind !== "rejected") return void 0;
    return { label: "Rejected", colorHex: import_theme.currentTheme.color("error") };
};

describe('test testpilot_subject', function() {

    it('returns undefined when toolCall.name is not "ExitPlanMode"', function() {
        // Arrange
        isExitPlanModeOutcomeOutput = function(o) { throw new Error("Should not be called"); };
        interpretExitPlanModeOutcome = function(o) { throw new Error("Should not be called"); };
        let inst = new testpilot_subject.file_0003.ToolCallComponent();
        inst.toolCall = { name: "SomeOtherMode" };
        inst.result = { output: "whatever" };

        // Act
        const res = inst.resolvePlanBoxStatus();

        // Assert
        assert.strictEqual(res, undefined);
    });

    })