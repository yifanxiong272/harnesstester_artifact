let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // reference to the function under test
    const removePathsFn = testpilot_subject.file_0001.FsWatcherService.prototype.removePaths;

    // Hold original import_di.dispose so we can restore later
    let importDi;
    let originalDispose;

    before(function() {
        // try to get the module that the implementation uses for dispose
        // (the implementation calls import_di.dispose). If it's not present,
        // tests that assert dispose behavior will be skipped.
        try {
            importDi = require('import_di');
            originalDispose = importDi.dispose;
        } catch (e) {
            importDi = null;
            originalDispose = null;
        }
    });

    after(function() {
        // restore original dispose if we replaced it
        if (importDi && originalDispose !== undefined) {
            importDi.dispose = originalDispose;
        }
    });

    it('returns [] immediately when store is disposed', function() {
        const thisObj = {
            _store: { isDisposed: true },
            sessions: new Map(),
            connections: new Map()
        };

        const res = removePathsFn.call(thisObj, 'anySession', 'anyConn', ['/x']);
        assert.deepStrictEqual(res, []);
    });

    })