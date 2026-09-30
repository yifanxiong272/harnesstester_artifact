let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to pull readable text from a render result in a tolerant way
    function extractText(result) {
        if (result === null || result === undefined) return String(result);
        if (typeof result === 'string') return result;
        if (typeof result === 'number' || typeof result === 'boolean') return String(result);
        // DOM-like nodes
        if (typeof result.textContent === 'string') return result.textContent;
        if (typeof result.innerText === 'string') return result.innerText;
        try {
            // Some objects implement toString usefully
            if (typeof result.toString === 'function') {
                let s = result.toString();
                if (s && s !== '[object Object]') return s;
            }
        } catch (e) {
            // ignore
        }
        try {
            return JSON.stringify(result);
        } catch (e) {
            // Fallback for circular objects
            return Object.prototype.toString.call(result);
        }
    }

    it('has a renderAskUserQuestionResult function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject must be present');
        assert.ok(testpilot_subject.file_0003, 'module.file_0003 must be present');
        let fn = testpilot_subject.file_0003.ToolCallComponent &&
                 testpilot_subject.file_0003.ToolCallComponent.prototype &&
                 testpilot_subject.file_0003.ToolCallComponent.prototype.renderAskUserQuestionResult;
        assert.strictEqual(typeof fn, 'function', 'renderAskUserQuestionResult should be a function');
    });

    })