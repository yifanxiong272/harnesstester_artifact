let mocha = require('mocha');
let assert = require('assert');
let os = require('os');
let fs = require('fs');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsService = testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService;

    it('FsService.resolvePath should exist and be an async function taking two arguments', function() {
        assert.ok(FsService, 'FsService class is not exported at testpilot_subject.file_0004.FsService');
        const fn = FsService.prototype.resolvePath;
        assert.ok(fn, 'resolvePath is not present on FsService.prototype');
        // Async functions have constructor name "AsyncFunction"
        assert.strictEqual(typeof fn, 'function', 'resolvePath is not a function');
        assert.strictEqual(fn.length, 2, 'resolvePath should declare two parameters (sessionId, relPath)');
        assert.strictEqual(fn.constructor && fn.constructor.name, 'AsyncFunction', 'resolvePath should be an async function');
    });

    })