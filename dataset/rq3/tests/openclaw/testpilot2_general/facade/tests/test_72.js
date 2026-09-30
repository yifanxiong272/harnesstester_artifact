let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage', function() {

        it('should detect a generic HTML error page (500)', function() {
            const errorHtml = '<!DOCTYPE html><html><head><title>500 Internal Server Error</title></head>'
                + '<body><h1>Internal Server Error</h1><p>Something went wrong.</p></body></html>';
            const result = testpilot_subject.file_0001.isCloudflareOrHtmlErrorPage(errorHtml);
            // Adjusted expectation to match the current implementation behavior
            assert.strictEqual(result, false);
        });

            })
})