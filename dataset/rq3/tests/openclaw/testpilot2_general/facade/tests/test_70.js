let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {

        it('should NOT treat normal (non-error) HTML pages as error pages', function() {
            const normalHtml = '<!DOCTYPE html><html><head><title>Home</title></head>'
                + '<body><h1>Welcome to the site</h1><p>Content here</p></body></html>';
            const result = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage(normalHtml);
            assert.strictEqual(result, false);
        });

            })
})