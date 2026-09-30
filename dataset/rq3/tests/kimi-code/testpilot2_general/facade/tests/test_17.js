let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.FsSearchService.None.dispose', function() {
    let NoneExport;
    let target; // the object whose dispose we'll call

    before(function() {
        // Make sure the module path exists; if not, skip the suite.
        if (!testpilot_subject ||
            !testpilot_subject.file_0002 ||
            !testpilot_subject.file_0002.FsSearchService ||
            !testpilot_subject.file_0002.FsSearchService.None) {
            this.skip();
            return;
        }

        NoneExport = testpilot_subject.file_0002.FsSearchService.None;

        // Determine whether NoneExport itself has dispose, or it's a constructor whose instances have dispose.
        if (typeof NoneExport.dispose === 'function') {
            target = NoneExport;
            return;
        }

        // If it's a constructor, try to instantiate one safely.
        if (typeof NoneExport === 'function' && typeof NoneExport.prototype !== 'undefined' && typeof NoneExport.prototype.dispose === 'function') {
            try {
                // Try to construct without arguments. If constructor requires args, skip the suite.
                target = new NoneExport();
                return;
            } catch (e) {
                // Could not instantiate - skip tests rather than failing due to unknown ctor requirements.
                this.skip();
                return;
            }
        }

        // If we reach here, we don't have a usable dispose function; skip.
        this.skip();
    });

    it('dispose should exist and be a function', function() {
        assert.ok(target, 'no target available to test dispose on');
        assert.strictEqual(typeof target.dispose, 'function', 'dispose is not a function');
    });

    })