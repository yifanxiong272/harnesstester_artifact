let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsService = testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService;

    it('FsService.prototype.dispose calls gitignoreCache.clear and then calls parent.dispose (order)', function() {
        if (!FsService) {
            this.skip(); // if class not present, skip the test
            return;
        }

        // Create a fake instance that uses FsService.prototype but we don't call the constructor.
        const instance = Object.create(FsService.prototype);

        // Prepare spies and order tracking.
        const calls = [];
        instance.gitignoreCache = {
            clear: function() {
                calls.push('clear');
            }
        };

        // Replace parent dispose with spy to detect call and order.
        const parentProto = Object.getPrototypeOf(FsService.prototype);
        const originalParentDispose = parentProto.dispose;
        let parentCalled = false;
        parentProto.dispose = function() {
            parentCalled = true;
            calls.push('parent');
        };

        try {
            // Invoke the method under test.
            FsService.prototype.dispose.call(instance);

            // Assertions: both functions called and in the right order.
            assert.strictEqual(parentCalled, true, 'parent.dispose should be called');
            assert.deepStrictEqual(calls, ['clear', 'parent'], 'gitignoreCache.clear should be called before parent.dispose');
        } finally {
            // Restore original parent dispose to avoid side effects on other tests.
            parentProto.dispose = originalParentDispose;
        }
    });

    })