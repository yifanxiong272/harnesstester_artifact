let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0017.normalizeMistralToolCallId', function() {
    it('returns first 9 alphanumeric characters when input has >= 9 alphanumerics', function() {
        const fn = testpilot_subject.file_0017.normalizeMistralToolCallId;
        // input already alphanumeric and longer than 9
        assert.strictEqual(fn('abcdefghiJKL'), 'abcdefghi');
        // input with non-alphanumerics mixed in, but resulting alphanumeric >= 9
        assert.strictEqual(fn('a!b@c#1$2%3^4&5(6)7_8+9='), 'abc123456');
        // numeric long string
        assert.strictEqual(fn('123456789012345'), '123456789');
    });

    })