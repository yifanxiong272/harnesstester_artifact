let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Polyfill Array.prototype.toSorted if not available in the runtime.
    if (!Array.prototype.toSorted) {
        Array.prototype.toSorted = function(compareFn) {
            // Make a shallow copy and sort it (toSorted returns a new array)
            return [...this].sort(compareFn);
        };
    }

    const fn = testpilot_subject.file_0003.ToolCallComponent.prototype.getRecentSubToolActivities;

    it('returns an empty array when subToolActivities is empty', function() {
        const fakeThis = { subToolActivities: new Map() };
        const res = fn.call(fakeThis);
        assert.deepStrictEqual(res, [], 'Expected empty array for empty subToolActivities');
    });

    })