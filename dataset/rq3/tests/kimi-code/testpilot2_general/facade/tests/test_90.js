let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: deep search an object for a reference to target
    function containsReference(root, target) {
        let visited = new Set();
        function _search(obj) {
            if (obj === target) return true;
            if (obj === null) return false;
            let t = typeof obj;
            if (t !== 'object' && t !== 'function') return false;
            if (visited.has(obj)) return false;
            visited.add(obj);

            // Check own property names and symbols
            let props = [];
            try { props = Object.getOwnPropertyNames(obj); } catch (e) {}
            try { props = props.concat(Object.getOwnPropertySymbols(obj)); } catch (e) {}

            for (let p of props) {
                let val;
                try { val = obj[p]; } catch (e) { continue; }
                if (val === target) return true;
                if (typeof val === 'object' || typeof val === 'function') {
                    if (_search(val)) return true;
                }
            }

            // If it's iterable like an array, try elements (covers some exotic cases)
            if (Array.isArray(obj)) {
                for (let i = 0; i < obj.length; i++) {
                    try {
                        if (obj[i] === target) return true;
                        if (_search(obj[i])) return true;
                    } catch (e) { /* ignore */ }
                }
            }

            return false;
        }
        return _search(root);
    }

    it('has a setSnapshotListener function on the prototype', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject must load');
        let proto = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype should exist');
        assert.strictEqual(typeof proto.setSnapshotListener, 'function', 'setSnapshotListener should be a function');
    });

    })