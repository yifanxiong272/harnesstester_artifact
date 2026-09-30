let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.FsService.prototype.dispose', function() {
        const FsService = testpilot_subject.file_0004.FsService;

        it('calls gitignoreCache.clear and calls parent dispose once', function() {
            const parentProto = Object.getPrototypeOf(FsService.prototype);
            const origParentDispose = parentProto.dispose;

            // spy for parent dispose
            let parentCalled = 0;
            parentProto.dispose = function() { parentCalled++; };

            try {
                // create a minimal instance without invoking constructor logic
                const inst = Object.create(FsService.prototype);
                inst.gitignoreCache = {
                    cleared: false,
                    clear() { this.cleared = true; }
                };

                const result = inst.dispose();
                // child dispose does not return parent's value (no return), expect undefined
                assert.strictEqual(result, undefined);
                assert.strictEqual(inst.gitignoreCache.cleared, true, 'gitignoreCache.clear was not called');
                assert.strictEqual(parentCalled, 1, 'super.dispose was not called exactly once');
            } finally {
                // restore original parent dispose (even if test failed)
                if (origParentDispose === undefined) {
                    delete parentProto.dispose;
                } else {
                    parentProto.dispose = origParentDispose;
                }
            }
        });

            })
})