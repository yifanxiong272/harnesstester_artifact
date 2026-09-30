let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.appendLiveOutput', function() {

        it('does nothing if this.result is defined', function() {
            // create a plain object that uses the prototype method without invoking constructor
            let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
            let comp = Object.create(proto);

            // initial state
            comp.liveOutput = 'initial';
            comp.result = 'finished'; // any defined value (!== void 0) should prevent appending

            let rebuildCalled = 0;
            let notifyCalled = 0;
            comp.rebuildContent = function() { rebuildCalled++; };
            comp.notifySnapshotChange = function() { notifyCalled++; };
            comp.ui = { requestRender: function() { throw new Error('should not call requestRender when result defined'); } };

            // attempt to append
            comp.appendLiveOutput('more');

            // nothing should have changed / been called
            assert.strictEqual(comp.liveOutput, 'initial', 'liveOutput must remain unchanged when result is defined');
            assert.strictEqual(rebuildCalled, 0, 'rebuildContent should not be called');
            assert.strictEqual(notifyCalled, 0, 'notifySnapshotChange should not be called');
        });

            })
})