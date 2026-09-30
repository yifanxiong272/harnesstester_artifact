let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.FsWatcherService.prototype.bindSessionCwd', function() {
        it('should exist and be a function on the prototype', function() {
            let proto = testpilot_subject.file_0001.FsWatcherService && testpilot_subject.file_0001.FsWatcherService.prototype;
            assert.ok(proto, 'FsWatcherService prototype is missing');
            assert.strictEqual(typeof proto.bindSessionCwd, 'function', 'bindSessionCwd should be a function');
        });

            })
})