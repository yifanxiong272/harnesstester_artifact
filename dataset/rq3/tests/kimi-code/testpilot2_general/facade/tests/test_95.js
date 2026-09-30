let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: a very tolerant "safe" sentinel that tolerates almost any property access, call, iteration.
    function makeSafe() {
        function f() { return f; }
        // make iterable (empty), convertible to primitive, and JSON-able
        f[Symbol.iterator] = function* () { /* empty iterator */ };
        f.toString = () => "__SAFE__";
        f.toJSON = () => "__SAFE__";
        f.valueOf = () => "__SAFE__";
        const handler = {
            get: () => f,
            apply: () => f,
            has: () => true
        };
        return new Proxy(f, handler);
    }

    // Create a 'this' object that has the given explicitProps and for any other property returns a safe sentinel.
    function makeThis(explicitProps) {
        explicitProps = explicitProps || {};
        const base = Object.assign({}, explicitProps);
        return new Proxy(base, {
            get(target, prop) {
                if (prop in target) return target[prop];
                return makeSafe();
            },
            has() { return true },
            // allow function-style use if something tries to call the object itself
            apply() { return makeSafe(); }
        });
    }

    // Simple deep clone via JSON for our plain-data assertions
    function jsonClone(x) {
        return JSON.parse(JSON.stringify(x));
    }

    it('ToolCallComponent.prototype.getReadSnapshot exists and is a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, "expected testpilot_subject.file_0003 to exist");
        const fn = testpilot_subject.file_0003.ToolCallComponent &&
                   testpilot_subject.file_0003.ToolCallComponent.prototype &&
                   testpilot_subject.file_0003.ToolCallComponent.prototype.getReadSnapshot;
        assert.strictEqual(typeof fn, 'function', 'getReadSnapshot should be a function on the prototype');
    });

    })