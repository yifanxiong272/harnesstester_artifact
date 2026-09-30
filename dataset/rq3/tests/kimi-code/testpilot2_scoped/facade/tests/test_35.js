let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs');
const os = require('os');
const path = require('path');

describe('test testpilot_subject', function() {
    let originalFsWatch;

    before(function() {
        // Basic sanity: the class should exist on the imported module.
        assert.ok(
            testpilot_subject &&
            testpilot_subject.file_0001 &&
            typeof testpilot_subject.file_0001.FsWatcherService === 'function',
            'FsWatcherService class not found on testpilot_subject.file_0001'
        );
    });

    beforeEach(function() {
        // save original fs.watch so we can restore it after each test
        originalFsWatch = fs.watch;
    });

    afterEach(function() {
        // restore original fs.watch
        fs.watch = originalFsWatch;
    });

    it('FsWatcherService.prototype.addPaths exists', function() {
        const proto = testpilot_subject.file_0001.FsWatcherService.prototype;
        assert.ok(proto, 'prototype missing');
        assert.strictEqual(typeof proto.addPaths, 'function', 'addPaths should be a function');
    });

    })