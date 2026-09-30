let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to check whether the returned value contains the expected substring/value
    function containsExpected(result, expected) {
        if (result === expected) return true;
        if (result == null) return false;

        // strings
        if (typeof result === 'string') {
            // accept exact match or containing expected (body might be embedded)
            return result === expected || result.indexOf(expected) !== -1;
        }

        // numbers
        if (typeof result === 'number' || typeof result === 'boolean') {
            return result === expected;
        }

        // arrays
        if (Array.isArray(result)) {
            return result.some(item => containsExpected(item, expected));
        }

        // objects: search values (shallow) for expected
        if (typeof result === 'object') {
            for (let k in result) {
                if (!Object.prototype.hasOwnProperty.call(result, k)) continue;
                if (containsExpected(result[k], expected)) return true;
            }
            return false;
        }

        // fallback
        try {
            return String(result).indexOf(String(expected)) !== -1;
        } catch (e) {
            return false;
        }
    }

    it('function exists and is callable', function() {
        assert.strictEqual(typeof testpilot_subject.file_0001.extractLeadingHttpStatus, 'function');
    });

    })