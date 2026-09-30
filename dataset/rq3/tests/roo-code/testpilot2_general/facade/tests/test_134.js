let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: create an instance of OutputManager. If constructor requires args or throws,
    // fall back to creating a plain object whose prototype is the OutputManager prototype.
    function createOutputManagerInstance() {
        let ctor = testpilot_subject.file_0002.OutputManager;
        try {
            return new ctor();
        } catch (e) {
            // fallback: create object with prototype so prototype methods can run
            return Object.create(ctor.prototype);
        }
    }

    // Helper: take a shallow->moderate snapshot of object properties up to a given depth.
    // We record primitive values and stringified versions for objects/functions.
    function snapshot(obj, maxDepth = 3) {
        let seen = new WeakSet();
        let result = {};

        function recurse(current, path, depth) {
            if (current !== Object(current)) {
                // primitive
                result[path] = current;
                return;
            }
            if (seen.has(current)) {
                result[path] = '[Circular]';
                return;
            }
            seen.add(current);

            if (depth <= 0) {
                result[path] = '[Object]';
                return;
            }

            // record own properties (including non-enumerable)
            try {
                let names = Object.getOwnPropertyNames(current);
                for (let name of names) {
                    // skip functions on the root prototype if those are methods; still record them as [Function]
                    let val;
                    try { val = current[name]; } catch (e) { val = '[Throw]'; }
                    let newPath = path ? (path + '.' + name) : name;
                    if (typeof val === 'function') {
                        result[newPath] = '[Function]';
                    } else if (val === null || val === undefined || typeof val !== 'object') {
                        result[newPath] = val;
                    } else {
                        recurse(val, newPath, depth - 1);
                    }
                }
            } catch (e) {
                // if getting property names throws for some object, mark it
                result[path] = '[Uninspectable]';
            }
        }

        recurse(obj, '', maxDepth);
        return result;
    }

    // Helper: find any snapshot paths where the after value loosely equals the provided ts,
    // and where the value either did not exist before or changed to this value.
    function findPathsSetTo(beforeSnap, afterSnap, ts) {
        let matches = [];
        let tsStr = String(ts);
        for (let p in afterSnap) {
            let afterVal = afterSnap[p];
            let beforeVal = beforeSnap.hasOwnProperty(p) ? beforeSnap[p] : undefined;
            // consider match if after equals ts (loose) and either didn't exist before or changed
            if (afterVal === undefined) continue;
            // Compare loosely: numbers stored as strings should still be accepted.
            let afterStr = (afterVal === null || afterVal === undefined) ? String(afterVal) : String(afterVal);
            if (afterStr === tsStr) {
                if (!beforeSnap.hasOwnProperty(p) || String(beforeVal) !== afterStr) {
                    matches.push(p);
                }
            }
        }
        return matches;
    }

    it('OutputManager.prototype.setLoggedFirstPartial should exist and be a function', function(done) {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace missing');
        let proto = testpilot_subject.file_0002.OutputManager && testpilot_subject.file_0002.OutputManager.prototype;
        assert.ok(proto, 'OutputManager prototype missing');
        assert.strictEqual(typeof proto.setLoggedFirstPartial, 'function', 'setLoggedFirstPartial should be a function on the prototype');
        done();
    });

    })