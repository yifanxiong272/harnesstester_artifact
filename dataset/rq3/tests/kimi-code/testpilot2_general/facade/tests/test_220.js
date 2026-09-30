let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let formatPhaseChip;
    before(function() {
        // Safely grab the method if it exists
        formatPhaseChip = testpilot_subject &&
                         testpilot_subject.file_0003 &&
                         testpilot_subject.file_0003.ToolCallComponent &&
                         testpilot_subject.file_0003.ToolCallComponent.prototype &&
                         testpilot_subject.file_0003.ToolCallComponent.prototype.formatPhaseChip;
    });

    it('formatPhaseChip should exist and be a function', function() {
        assert.ok(formatPhaseChip, 'formatPhaseChip is not found on prototype');
        assert.strictEqual(typeof formatPhaseChip, 'function', 'formatPhaseChip is not a function');
    });

    })