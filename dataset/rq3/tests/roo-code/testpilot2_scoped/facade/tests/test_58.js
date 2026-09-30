let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0007.convertToR1Format', function() {
    it('should export a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0007, 'file_0007 export should be present');
        assert.strictEqual(typeof testpilot_subject.file_0007.convertToR1Format, 'function',
            'convertToR1Format should be a function');
    });

    })