let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ToolCallComponent = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent;
    const method = ToolCallComponent && ToolCallComponent.prototype && ToolCallComponent.prototype.buildAgentSwarmResultSummary;

    // helper deep clone
    const clone = (o) => {
        try {
            return JSON.parse(JSON.stringify(o));
        } catch (e) {
            // fallback for non-serializable inputs (not used here)
            return o;
        }
    };

    it('buildAgentSwarmResultSummary should exist', function(done) {
        assert.ok(typeof method === 'function', 'expected buildAgentSwarmResultSummary to be a function');
        done();
    });

    })