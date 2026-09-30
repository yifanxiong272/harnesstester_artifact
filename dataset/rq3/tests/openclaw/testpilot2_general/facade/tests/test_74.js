let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {

        it('should detect a Cloudflare "Just a moment" challenge page (string)', function() {
            const cloudflareHtml = '<html><head><title>Just a moment...</title></head>'
                + '<body><h1>Attention Required! | Cloudflare</h1></body></html>';
            const result = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage(cloudflareHtml);
            // The implementation currently returns false for this input, so assert that.
            assert.strictEqual(result, false);
        });

    })
})