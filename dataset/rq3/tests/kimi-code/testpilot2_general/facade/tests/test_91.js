let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.setSnapshotListener', function() {

        it('calls listener immediately and sets onSnapshotChange to the function', function() {
            // create object whose prototype is the ToolCallComponent prototype without running constructor
            let obj = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);

            let called = 0;
            function cb() { called += 1; }

            obj.setSnapshotListener(cb);

            assert.strictEqual(obj.onSnapshotChange, cb, 'onSnapshotChange should be set to the provided function');
            assert.strictEqual(called, 1, 'callback should be invoked immediately once');
        });

            })
})