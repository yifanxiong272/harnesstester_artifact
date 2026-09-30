let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to try several common ways to read the stored value
    function readMinComponentLines() {
        const obj = testpilot_subject.file_0010;
        if (!obj) return undefined;
        if (typeof obj.minComponentLines !== 'undefined') return obj.minComponentLines;
        if (typeof obj.getMinComponentLines === 'function') return obj.getMinComponentLines();
        if (typeof obj.get_min_component_lines === 'function') return obj.get_min_component_lines();
        return undefined;
    }

    it('should export setMinComponentLines as a function', function(done) {
        try {
            assert.ok(testpilot_subject.file_0010, 'file_0010 should exist on the module');
            assert.strictEqual(typeof testpilot_subject.file_0010.setMinComponentLines, 'function',
                'setMinComponentLines should be a function');
            done();
        } catch (err) {
            done(err);
        }
    });

    })