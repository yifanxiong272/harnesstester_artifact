let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0016.shouldStripProviderAuthEnvVarsForAcpServer;

    it('returns true when no params or serverCommand is not provided', function(done) {
        // no params
        assert.strictEqual(fn(), true);
        // explicit empty object
        assert.strictEqual(fn({}), true);
        done();
    });

    })