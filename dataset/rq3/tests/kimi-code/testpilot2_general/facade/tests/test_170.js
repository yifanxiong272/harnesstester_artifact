let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject &&
                  testpilot_subject.file_0003 &&
                  testpilot_subject.file_0003.ToolCallComponent &&
                  testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('ToolCallComponent.prototype.getAgentToolDescription should exist and be a function', function() {
        assert.ok(proto, 'ToolCallComponent prototype is available on testpilot_subject.file_0003');
        assert.strictEqual(typeof proto.getAgentToolDescription, 'function',
            'getAgentToolDescription should be a function on the prototype');
    });

    })