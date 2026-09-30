let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Provide minimal implementations of helpers the method expects.
    // Save originals so tests do not permanently tamper with global state.
    const originalStr = global.str;
    const originalExtractApprovedPlan = global.extractApprovedPlan;

    before(function() {
        // str(x) should behave like the original helper: return empty string for null/undefined,
        // return the string for strings, otherwise String(value).
        global.str = function(v) {
            if (v === undefined || v === null) return "";
            if (typeof v === "string") return v;
            return String(v);
        };

        // extractApprovedPlan should extract an approvedPlan property if present,
        // otherwise return empty string. Tests will provide outputs that match this.
        global.extractApprovedPlan = function(output) {
            if (!output) return "";
            if (typeof output === "string") return output; // allow string outputs for simplicity
            if (typeof output.approvedPlan === "string") return output.approvedPlan;
            return "";
        };
    });

    after(function() {
        // Restore globals
        global.str = originalStr;
        global.extractApprovedPlan = originalExtractApprovedPlan;
    });

    it('returns inline plan when toolCall.args.plan is a non-empty string', function() {
        const fn = testpilot_subject.file_0003.ToolCallComponent.prototype.resolvePlanForPreview;
        const ctx = {
            toolCall: { args: { plan: "inline plan text" } },
            result: { is_error: false, output: { approvedPlan: "approved plan text" } },
            currentPlan: "current plan text"
        };
        const out = fn.call(ctx);
        assert.strictEqual(out, "inline plan text");
    });

    })