let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // reference to the prototype method under test
    const proto = testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype;
    const cancel = proto.cancelAuthorizationFlow;

    it('should be a function on the prototype', function() {
        assert.strictEqual(typeof cancel, 'function', 'cancelAuthorizationFlow should be a function');
    });

    })