let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('handles empty or non-matching input gracefully', function() {
        // empty string
        let r1 = testpilot_subject.file_0001.parseImageDimensionError('');
        // null
        let r2 = testpilot_subject.file_0001.parseImageDimensionError(null);
        // a non-matching arbitrary string
        let r3 = testpilot_subject.file_0001.parseImageDimensionError('no dimensions here');

        // Expect the function not to throw and to return a falsy or empty-like result for non-matching input.
        // We accept undefined, null, false, empty string, or an empty object/array.
        function isEmptyLike(x) {
            if (!x) return true;
            if (Array.isArray(x)) return x.length === 0;
            if (typeof x === 'object') return Object.keys(x).length === 0;
            return false;
        }

        assert.ok(isEmptyLike(r1), 'empty input should produce an empty-like result');
        assert.ok(isEmptyLike(r2), 'null input should produce an empty-like result');
        assert.ok(isEmptyLike(r3), 'non-matching input should produce an empty-like result');
    });
});