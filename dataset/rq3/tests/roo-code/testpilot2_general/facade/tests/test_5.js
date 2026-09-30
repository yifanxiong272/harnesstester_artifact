let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to spy on common console methods
    function spyAllConsole() {
        const methods = ['log', 'info', 'warn', 'error', 'debug'];
        const original = {};
        const calls = [];
        methods.forEach(m => {
            original[m] = console[m];
            console[m] = function(...args) {
                calls.push({ method: m, args });
                // don't call original to avoid noisy output
            };
        });
        return {
            calls,
            restore: () => {
                methods.forEach(m => {
                    console[m] = original[m];
                });
            }
        };
    }

    it('has OpenAiCodexOAuthManager and a log method on its prototype', function(done) {
        const Manager = testpilot_subject.file_0001 && testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        assert.ok(Manager, 'OpenAiCodexOAuthManager should be present');
        assert.strictEqual(typeof Manager.prototype.log, 'function', 'log should be a function on the prototype');
        done();
    });

    })