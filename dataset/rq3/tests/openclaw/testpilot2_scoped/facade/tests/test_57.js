let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {
    const fn = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage;

    it('returns false for empty / whitespace-only input', function() {
        assert.strictEqual(fn(''), false);
        assert.strictEqual(fn('   \n\t  '), false);
    });

    })