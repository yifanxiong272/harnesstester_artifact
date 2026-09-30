let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper that handles synchronous or promise-returning implementations
    function check(raw, expected, done) {
        try {
            let result = testpilot_subject.file_0001.isAuthErrorMessage(raw);
            if (result && typeof result.then === 'function') {
                // function returned a promise
                result.then(function(res) {
                    assert.strictEqual(res, expected);
                    done();
                }).catch(done);
            } else {
                // synchronous result
                assert.strictEqual(result, expected);
                done();
            }
        } catch (err) {
            done(err);
        }
    }

    it('returns true for explicit "Authentication failed" messages', function(done) {
        check("Authentication failed: Invalid password", true, done);
    });

    })