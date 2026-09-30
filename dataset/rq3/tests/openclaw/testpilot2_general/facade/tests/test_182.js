let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subjectPath = ['file_0005', 'processTool', 'execute'];
    function getSubjectFunction() {
        // Navigate defensively to the function under test
        let cur = testpilot_subject;
        for (const p of subjectPath) {
            if (!cur) return undefined;
            cur = cur[p];
        }
        return cur;
    }

    it('exports an execute function at testpilot_subject.file_0005.processTool.execute', function() {
        const fn = getSubjectFunction();
        assert.ok(fn, 'expected function to be present');
        assert.strictEqual(typeof fn, 'function', 'expected execute to be a function');
    });

    })