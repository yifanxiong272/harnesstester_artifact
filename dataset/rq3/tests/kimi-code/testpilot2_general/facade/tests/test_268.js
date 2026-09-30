let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

// Some environments don't provide these modules as bare imports.
// Fall back to simple stubs if the require fails so the test can run.
let import_plan_box;
try {
    import_plan_box = require('import_plan_box');
} catch (e) {
    import_plan_box = { PlanBoxComponent: undefined };
}

let import_theme;
try {
    import_theme = require('import_theme');
} catch (e) {
    import_theme = { currentTheme: { color: undefined } };
}

describe('test testpilot_subject', function() {
    // Save originals so we can restore after tests
    let PlanBoxOriginal = import_plan_box.PlanBoxComponent;
    let themeColorOriginal = import_theme && import_theme.currentTheme ? import_theme.currentTheme.color : undefined;

    after(function() {
        // Restore originals to avoid side effects
        import_plan_box.PlanBoxComponent = PlanBoxOriginal;
        if (import_theme && import_theme.currentTheme && themeColorOriginal !== undefined) {
            import_theme.currentTheme.color = themeColorOriginal;
        }
    });

    it('does nothing (does not add child) when resolvePlanForPreview returns an empty plan', function() {
        // Create an instance-like object that uses the ToolCallComponent prototype method
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        const comp = Object.create(proto);

        // Stub methods/properties used by buildPlanPreview
        comp.resolvePlanForPreview = function() { return []; };
        let childAdded = false;
        comp.addChild = function() { childAdded = true; };

        // Call method under test
        comp.buildPlanPreview();

        // Expect no child to have been added
        assert.strictEqual(childAdded, false);
    });

    })