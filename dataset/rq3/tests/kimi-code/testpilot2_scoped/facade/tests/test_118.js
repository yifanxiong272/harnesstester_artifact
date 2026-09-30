let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.KimiCore.prototype.reloadSession', function() {
        const reload = testpilot_subject
            && testpilot_subject.file_0002
            && testpilot_subject.file_0002.KimiCore
            && testpilot_subject.file_0002.KimiCore.prototype
            && testpilot_subject.file_0002.KimiCore.prototype.reloadSession;

        it('should exist and be an async function', function() {
            assert.ok(reload, 'reloadSession is not present on prototype');
            // Async functions have constructor named "AsyncFunction"
            assert.strictEqual(
                typeof reload,
                'function',
                'reloadSession should be a function'
            );
            // Some environments expose the constructor name; check if it's an async function
            // If constructor name isn't available, at least ensure calling it returns a Promise/thenable.
            const ctorName = reload.constructor && reload.constructor.name;
            if (ctorName) {
                assert.strictEqual(
                    ctorName,
                    'AsyncFunction',
                    'reloadSession should be an async function (constructor name AsyncFunction)'
                );
            }
        });

            })
})