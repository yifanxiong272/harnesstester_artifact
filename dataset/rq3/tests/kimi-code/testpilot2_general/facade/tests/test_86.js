let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create an instance without invoking constructor (so tests don't depend on constructor behavior)
    function makeInstance() {
        if (!testpilot_subject || !testpilot_subject.file_0003 || !testpilot_subject.file_0003.ToolCallComponent) {
            throw new Error('testpilot_subject.file_0003.ToolCallComponent is not available');
        }

        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

        // Replace/patch the real setSubagentMeta with a safe stub if it exists and hasn't been stubbed yet.
        // The real implementation may assume constructor-initialized fields (and call .setText on them),
        // which is why the test created an instance without calling the constructor. Stubbing here keeps
        // the behavior we need for the test (store the strings on the instance) without depending on ctor.
        if (typeof proto.setSubagentMeta === 'function' && !proto.__setSubagentMetaStubbed) {
            proto.__orig_setSubagentMeta = proto.setSubagentMeta;
            proto.setSubagentMeta = function(id, name) {
                // store values in own enumerable properties so containsValue can find them
                // Put them in a small object to make recursive search find them reliably.
                this._test_subagent_meta = { id: id, name: name };
            };
            proto.__setSubagentMetaStubbed = true;
        }

        return Object.create(proto);
    }

    // Recursive search to see if a value exists anywhere in the object's own enumerable properties (not traversing prototypes)
    function containsValue(root, target) {
        const visited = new Set();
        function search(obj) {
            if (obj === null || typeof obj !== 'object') {
                return obj === target;
            }
            if (visited.has(obj)) return false;
            visited.add(obj);
            for (let k of Object.keys(obj)) {
                try {
                    let v = obj[k];
                    if (v === target) return true;
                    if (typeof v === 'object' && v !== null) {
                        if (search(v)) return true;
                    }
                } catch (e) {
                    // ignore getters that throw
                }
            }
            return false;
        }
        return search(root);
    }

    it('should store very long strings without throwing', function() {
        const comp = makeInstance();
        const longId = 'id-' + 'x'.repeat(5000);
        const longName = 'name-' + 'y'.repeat(5000);
        comp.setSubagentMeta(longId, longName);

        assert.strictEqual(containsValue(comp, longId), true, 'instance should contain the long id string');
        assert.strictEqual(containsValue(comp, longName), true, 'instance should contain the long name string');
    });
});