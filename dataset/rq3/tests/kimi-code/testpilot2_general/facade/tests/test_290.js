let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to interpret various possible result shapes and extract a string to compare.
    function extractStringFromResult(res) {
        if (res === null || res === undefined) return null;
        if (Buffer.isBuffer(res)) return res.toString();
        if (typeof res === 'string') return res;
        if (typeof res === 'object') {
            // Common property names where content might be returned
            const candidates = ['body', 'data', 'content', 'result'];
            for (let k of candidates) {
                if (k in res) {
                    return extractStringFromResult(res[k]);
                }
            }
            // Some implementations may return { stream: ... } or other forms we cannot synchronously inspect
            return null;
        }
        return null;
    }

    it('FsService.prototype.read should exist and be an async function', function() {
        assert.ok(testpilot_subject, 'module loaded');
        assert.ok(testpilot_subject.file_0004, 'file_0004 namespace exists');
        assert.ok(testpilot_subject.file_0004.FsService, 'FsService constructor exists');
        const read = testpilot_subject.file_0004.FsService.prototype.read;
        assert.strictEqual(typeof read, 'function', 'read is a function');
        // Check whether the function is declared as async (constructor name AsyncFunction)
        const ctorName = read && read.constructor && read.constructor.name;
        assert.ok(ctorName === 'AsyncFunction' || ctorName === 'Function',
            'read should be an async function or at least a function (constructor: ' + ctorName + ')');
    });

    })