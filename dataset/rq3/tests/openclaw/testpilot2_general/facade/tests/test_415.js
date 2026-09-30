let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0014.filterToolResultMediaUrls - returns same array when empty', function(done) {
        const fn = testpilot_subject.file_0014.filterToolResultMediaUrls;
        let arr = [];
        let result = fn('someTool', arr, {});
        // should return the same array reference when empty
        assert.strictEqual(result, arr);
        assert.deepStrictEqual(result, []);
        done();
    });

    })