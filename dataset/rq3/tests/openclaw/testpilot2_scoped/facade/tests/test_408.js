let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.completionCacheExists', function() {
        // confirm module shape we expect
        it('should have the completionCacheExists function', function() {
            assert.strictEqual(typeof testpilot_subject.file_0015.completionCacheExists, 'function');
        });

            })
})