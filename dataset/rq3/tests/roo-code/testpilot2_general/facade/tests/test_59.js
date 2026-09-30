let mocha = require('mocha');
let assert = require('assert');
let { URL } = require('url');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.buildAuthorizationUrl', function() {
        it('produces distinct URLs for different inputs', function() {
            const a1 = testpilot_subject.file_0001.buildAuthorizationUrl('codeOne', 'stateOne');
            const a2 = testpilot_subject.file_0001.buildAuthorizationUrl('codeTwo', 'stateOne');
            const a3 = testpilot_subject.file_0001.buildAuthorizationUrl('codeOne', 'stateTwo');

            // All should be strings
            assert.strictEqual(typeof a1, 'string');
            assert.strictEqual(typeof a2, 'string');
            assert.strictEqual(typeof a3, 'string');

            // Changing code challenge or state should change the resulting URL
            assert.notStrictEqual(a1, a2);
            assert.notStrictEqual(a1, a3);
            assert.notStrictEqual(a2, a3);
        });
    });
});