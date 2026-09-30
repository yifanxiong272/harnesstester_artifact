let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {

        it('should NOT flag non-HTML JSON payloads', function() {
            const json = JSON.stringify({ status: 'ok', data: [1,2,3] });
            const res = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage(json);
            assert.strictEqual(res, false, 'JSON payload should not be identified as an HTML error page');
        });

            })
})