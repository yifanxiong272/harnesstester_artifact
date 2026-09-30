let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.applySubagentReplay - no subagent (early return)', function(done) {
        // Grab the method implementation
        const apply = testpilot_subject.file_0003.ToolCallComponent.prototype.applySubagentReplay;

        // Create a dummy "this" object with sentinel values
        const obj = {
            subagentAgentId: 'INITIAL_ID',
            subagentAgentName: 'INITIAL_NAME',
            subagentText: 'INITIAL_TEXT',
            ongoingSubCalls: new Map([['existing','value']]),
            finishedSubCalls: [{name:'existing', args:{}, output:'x', isError:false}],
            hiddenSubCallCount: 7,
            upsertCalls: [],
            upsertSubToolActivity: function() { this.upsertCalls.push(Array.from(arguments)); }
        };

        // Call with undefined -> should return early and not change obj
        apply.call(obj, undefined);

        assert.strictEqual(obj.subagentAgentId, 'INITIAL_ID');
        assert.strictEqual(obj.subagentAgentName, 'INITIAL_NAME');
        assert.strictEqual(obj.subagentText, 'INITIAL_TEXT');
        assert.strictEqual(obj.ongoingSubCalls.get('existing'), 'value');
        assert.strictEqual(obj.finishedSubCalls.length, 1);
        assert.strictEqual(obj.hiddenSubCallCount, 7);
        assert.strictEqual(obj.upsertCalls.length, 0);

        done();
    });

    })