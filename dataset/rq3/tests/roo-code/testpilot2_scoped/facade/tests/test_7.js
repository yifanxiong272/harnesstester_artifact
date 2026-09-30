let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let util = require('util');

let writeFile = util.promisify(fs.writeFile);
let unlink = util.promisify(fs.unlink);
let mkdtemp = util.promisify(fs.mkdtemp);
let rmdir = util.promisify(fs.rmdir);

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // small helper to treat several "empty" return shapes as acceptable
    function isEmptyResult(res) {
        if (res == null) return true; // null or undefined
        if (Array.isArray(res)) return res.length === 0;
        if (typeof res === 'object') return Object.keys(res).length === 0;
        if (typeof res === 'string') return res.trim().length === 0;
        return false;
    }

    it('exports file_0003.parseSourceCodeDefinitionsForFile as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'expected file_0003 namespace');
        assert.strictEqual(typeof testpilot_subject.file_0003.parseSourceCodeDefinitionsForFile, 'function');
    });

    })