let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.upsertSubToolActivity', function() {

        it('inserts a new sub-tool activity with output and sets orderSeq', function(done) {
            // Create an object that uses the prototype method but supply our own storage
            const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
            const component = Object.create(ToolCallComponent.prototype);
            component.subToolActivities = new Map();
            component.subToolOrderSeq = 0;

            const id = 'a1';
            const name = 'tool1';
            const args = { x: 1 };
            const phase = 'start';
            const output = { result: 42 };

            // call method under test
            component.upsertSubToolActivity(id, name, args, phase, output);

            // verify map entry exists
            assert.strictEqual(component.subToolActivities.has(id), true);
            const activity = component.subToolActivities.get(id);

            // verify fields
            assert.strictEqual(activity.id, id);
            assert.strictEqual(activity.name, name);
            assert.deepStrictEqual(activity.args, args);
            assert.strictEqual(activity.phase, phase);
            assert.deepStrictEqual(activity.output, output);

            // orderSeq should have been incremented from 0 to 1
            assert.strictEqual(activity.orderSeq, 1);
            assert.strictEqual(component.subToolOrderSeq, 1);

            done();
        });

            })
})