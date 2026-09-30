let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to get the prototype where setExpanded lives
    function getPrototype() {
        if (!testpilot_subject || !testpilot_subject.file_0003 || !testpilot_subject.file_0003.ToolCallComponent) {
            throw new Error('Required testpilot_subject.file_0003.ToolCallComponent not found');
        }
        return testpilot_subject.file_0003.ToolCallComponent.prototype;
    }

    it('does not call rebuildBody when expanded is unchanged (strict equality)', function() {
        const proto = getPrototype();
        // Create an object that uses the prototype so we can test the method in isolation
        const obj = Object.create(proto);
        // set initial expanded to true
        obj.expanded = true;
        let rebuildCalls = 0;
        obj.rebuildBody = function() { rebuildCalls++; };

        // Call with the same value; should early-return and not call rebuildBody
        obj.setExpanded(true);

        assert.strictEqual(obj.expanded, true, 'expanded should remain true');
        assert.strictEqual(rebuildCalls, 0, 'rebuildBody should not have been called');
    });

    })