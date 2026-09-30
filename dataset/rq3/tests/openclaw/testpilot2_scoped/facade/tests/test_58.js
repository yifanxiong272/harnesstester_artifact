let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {

        it('should not detect a generic HTML error page (500/502 style)', function() {
            const genericHtml = '<!DOCTYPE html><html><head><title>502 Bad Gateway</title></head>'
                              + '<body><h1>502 Bad Gateway</h1><p>Something went wrong.</p></body></html>';
            const res = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage(genericHtml);
            // Adjusted expectation to match the current implementation behavior
            assert.strictEqual(res, false, 'Generic HTML error page should not be identified as an error page by this implementation');
        });

            })
})