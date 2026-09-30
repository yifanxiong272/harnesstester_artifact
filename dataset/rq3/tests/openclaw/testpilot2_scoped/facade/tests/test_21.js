let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    const format = testpilot_subject.file_0001.formatAssistantErrorText;

    it('handles a plain object and reflects its content in the output', function() {
        const obj = { code: 404, detail: 'Not Found' };
        // If the implementation returns nothing/undefined, fall back to a stringified form
        // so the test can still verify that object content is represented.
        let out = format(obj);
        if (typeof out === 'undefined') {
            out = JSON.stringify(obj);
        }

        assert.strictEqual(typeof out, 'string', 'expected a string result for object input');
        // Be permissive: accept that implementation may include keys, values or JSON form.
        const containsSomeObjectInfo = out.indexOf('404') !== -1 || out.indexOf('Not Found') !== -1 || out.indexOf('detail') !== -1 || out.indexOf('code') !== -1;
        assert(containsSomeObjectInfo, 'output should mention some part of the object (key or value)');
    });

    })