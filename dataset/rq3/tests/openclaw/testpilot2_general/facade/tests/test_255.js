let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.normalizeExecHost - should not throw for a variety of inputs', function(done) {
        try {
            let fn = testpilot_subject.file_0009.normalizeExecHost;
            let inputs = [
                undefined,
                null,
                '',
                'example.com',
                ' example.com ',
                '\thost.example.org\n',
                'EXAMPLE.COM:8080',
                '127.0.0.1',
                'http://example.com',
                'user@host',
            ];

            inputs.forEach(function(input) {
                assert.doesNotThrow(function() {
                    fn(input);
                }, Error, 'normalizeExecHost threw for input: ' + String(input));
            });

            done();
        } catch (err) {
            done(err);
        }
    });

    })