let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let util = require('util');

let testpilot_subject = require('..');

describe('test testpilot_subject.file_0018.openWritableFileWithinRoot', function() {
    // convenience reference
    const fn = testpilot_subject && testpilot_subject.file_0018 && testpilot_subject.file_0018.openWritableFileWithinRoot;

    it('exports an async function', function() {
        assert.ok(fn, 'function is not exported at testpilot_subject.file_0018.openWritableFileWithinRoot');
        // util.types.isAsyncFunction is the most direct check for async functions
        assert.ok(util.types.isAsyncFunction(fn), 'openWritableFileWithinRoot should be an async function');
    });

    })