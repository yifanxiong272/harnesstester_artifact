let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns empty string when both subagentThinkingText and subagentText are empty', function(done) {
        // create an instance without calling any constructor (avoid side-effects)
        const inst = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
        inst.subagentThinkingText = "";
        inst.subagentText = "";
        const result = inst.getCombinedSubagentText();
        assert.strictEqual(result, "");
        done();
    });

    })