let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0004.convertToolBlocksToText', function() {
    const convert = testpilot_subject &&
                    testpilot_subject.file_0004 &&
                    testpilot_subject.file_0004.convertToolBlocksToText;

    it('exports a function', function() {
        assert.ok(convert, 'convertToolBlocksToText should be exported');
        assert.strictEqual(typeof convert, 'function');
    });

    })