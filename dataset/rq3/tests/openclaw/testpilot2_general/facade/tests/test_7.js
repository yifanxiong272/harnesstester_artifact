let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.extractLeadingHttpStatus', function() {

        function containsStatus200(result) {
            if (result === null || result === undefined) return false;
            if (typeof result === 'number') return result === 200;
            if (typeof result === 'string') return result.indexOf('200') !== -1 || result.indexOf('OK') !== -1;
            if (typeof result === 'object') {
                if ('status' in result && result.status === 200) return true;
                if ('statusCode' in result && result.statusCode === 200) return true;
                if ('code' in result && result.code === 200) return true;
                // fallback: stringified content might contain status/message
                try {
                    let s = JSON.stringify(result);
                    return s.indexOf('200') !== -1 || s.indexOf('OK') !== -1;
                } catch (e) {
                    return false;
                }
            }
            return false;
        }

        it('should return a falsy value when there is no leading HTTP status', function() {
            let raw = "This is not an HTTP response\r\nJust some text";
            let res = testpilot_subject.file_0001.extractLeadingHttpStatus(raw);
            // Conservative expectation: when there is no leading HTTP status, the extractor should return a falsy result
            // (null/undefined/false). Accepting falsy keeps the test robust against common implementations.
            assert.ok(!res, 'expected a falsy result (null/undefined/false) when input does not start with an HTTP status line');
        });

            })
})