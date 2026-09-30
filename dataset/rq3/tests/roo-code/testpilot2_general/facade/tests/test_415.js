let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0010.getMinComponentLines - is a function and returns a stable value', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0010, 'file_0010 should exist on testpilot_subject');

        const fn = testpilot_subject.file_0010.getMinComponentLines;
        assert.strictEqual(typeof fn, 'function', 'getMinComponentLines should be a function');

        // Multiple calls should be consistent (idempotent getter)
        const v1 = fn();
        const v2 = fn();
        assert.strictEqual(v1, v2, 'Repeated calls should return the same value');

        // The return type should be either a number or undefined (handle module variations)
        const t = typeof v1;
        assert.ok(t === 'number' || t === 'undefined', 'Return type should be number or undefined');
    });

    })