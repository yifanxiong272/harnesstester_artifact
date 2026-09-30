let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.detectCursorKeyMode', function() {
        let detect = testpilot_subject.file_0008.detectCursorKeyMode;

        it('should handle empty or unrelated input gracefully (falsy result)', function() {
            // empty string / empty buffer / unrelated bytes should not claim a mode
            let emptyStr = '';
            let emptyBuf = Buffer.alloc(0);
            let garbage = Buffer.from([0x01, 0x02, 0x03]);

            let rEmptyStr = detect(emptyStr);
            let rEmptyBuf = detect(emptyBuf);
            let rGarbage = detect(garbage);

            // Expect falsy results for these inputs (null/undefined/false/0/'')
            assert.ok(!rEmptyStr, 'Empty string input should yield a falsy detection');
            assert.ok(!rEmptyBuf, 'Empty buffer input should yield a falsy detection');
            assert.ok(!rGarbage, 'Unrelated bytes should yield a falsy detection');
        });
    });
});