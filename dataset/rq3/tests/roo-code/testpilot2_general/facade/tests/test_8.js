let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper that calls initialize and normalizes both sync and promise returns to a Promise
    function runInitializeAsync(instance, context, logFn) {
        try {
            const ret = instance.initialize(context, logFn);
            if (ret && typeof ret.then === 'function') {
                return ret;
            } else {
                return Promise.resolve(ret);
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('has OpenAiCodexOAuthManager with an initialize function on the prototype', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0001, 'file_0001 should exist on module');
        const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        assert.ok(Manager, 'OpenAiCodexOAuthManager constructor should exist');
        assert.ok(typeof Manager.prototype.initialize === 'function', 'initialize should be a function on prototype');
    });

    })