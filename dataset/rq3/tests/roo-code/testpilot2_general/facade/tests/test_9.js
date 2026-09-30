let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.initialize - sets context and logFn when provided', function() {
        let mgr = new testpilot_subject.file_0001.OpenAiCodexOAuthManager();
        let ctx = { some: 'context' };
        let logger = function() { return 'logged'; };

        let ret = mgr.initialize(ctx, logger);

        // initialize does not return anything (undefined)
        assert.strictEqual(ret, undefined);

        // properties should be set to provided values
        assert.strictEqual(mgr.context, ctx);
        assert.strictEqual(mgr.logFn, logger);
    });

    })