let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0023.mergeConsecutiveApiMessages;

    it('returns the same array reference if messages length <= 1', function() {
        const single = [{ role: 'user', content: [{type:'text', text:'only'}], ts: 123 }];
        const res = fn(single);
        // function returns the same array if length <= 1
        assert.strictEqual(res, single);
    });

    })