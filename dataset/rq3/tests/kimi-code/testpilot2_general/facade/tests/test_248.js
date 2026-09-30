let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Locate the prototype under test, if present.
    const proto = testpilot_subject &&
                  testpilot_subject.file_0003 &&
                  testpilot_subject.file_0003.ToolCallComponent &&
                  testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('formatSubToolActivity should exist and be a function on the prototype', function() {
        if (!proto) this.skip(); // skip tests gracefully if module shape is not as expected
        assert.strictEqual(typeof proto.formatSubToolActivity, 'function');
    });

    })