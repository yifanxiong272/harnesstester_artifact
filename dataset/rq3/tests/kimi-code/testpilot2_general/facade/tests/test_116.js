let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.isDetachHintEligible', function() {
    const Prototype = testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('returns true when toolCall.name is exactly "Bash"', function() {
        let inst = Object.create(Prototype);
        inst.toolCall = { name: "Bash" };
        assert.strictEqual(inst.isDetachHintEligible(), true);
    });

    })