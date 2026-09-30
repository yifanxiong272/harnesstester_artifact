let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure tests have enough time in case implementations use async timers
    this.timeout(5000);

    it('test testpilot_subject.file_0004.FsService.prototype.listMany - exists and is async', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0004, 'expected file_0004 namespace to exist');
        const FsService = testpilot_subject.file_0004.FsService;
        assert.ok(FsService, 'expected FsService to exist');
        // The listMany method should be present on the prototype
        const listMany = FsService.prototype.listMany;
        assert.strictEqual(typeof listMany, 'function', 'listMany should be a function');

        // Async functions have constructor name "AsyncFunction"
        const ctorName = listMany.constructor && listMany.constructor.name;
        assert.strictEqual(ctorName, 'AsyncFunction', 'listMany should be an async function (AsyncFunction)');
    });

    })