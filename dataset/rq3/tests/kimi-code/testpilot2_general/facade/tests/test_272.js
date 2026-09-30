let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const file = testpilot_subject.file_0003;
    const proto = file.ToolCallComponent.prototype;
    let originalInterpret;

    before(function() {
        // backup any existing interpretExitPlanModeOutcome so tests can safely override it
        originalInterpret = file.interpretExitPlanModeOutcome;
    });

    after(function() {
        // restore original to avoid side effects on other tests
        file.interpretExitPlanModeOutcome = originalInterpret;
    });

    it('returns planPath when result is undefined', function() {
        const obj = Object.create(proto);
        obj.planPath = 'expected/plan/path';
        obj.result = undefined;
        const res = obj.resolvePlanPath();
        assert.strictEqual(res, 'expected/plan/path');
    });

    })