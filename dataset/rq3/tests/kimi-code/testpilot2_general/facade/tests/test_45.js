let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // simple helper to create a temporary directory with a few files
    function makeTempTree() {
        const base = fs.mkdtempSync(path.join(os.tmpdir(), 'fsp-test-'));
        // create a few files and a subdirectory
        fs.writeFileSync(path.join(base, 'a.txt'), 'alpha');
        fs.writeFileSync(path.join(base, 'b.js'), 'beta');
        const sub = path.join(base, 'sub');
        fs.mkdirSync(sub);
        fs.writeFileSync(path.join(sub, 'c.md'), 'gamma');
        return base;
    }

    // cleanup helper
    function rmrf(target) {
        try {
            fs.rmSync(target, { recursive: true, force: true });
        } catch (e) {
            // fallback for older Node versions
            try {
                // sync recursive rmdir
                const rimraf = require('rimraf');
                rimraf.sync(target);
            } catch (_) {}
        }
    }

    it('FsSearchService.prototype.matcher exists and is async', function() {
        const proto = testpilot_subject.file_0002.FsSearchService.prototype;
        assert.strictEqual(typeof proto.matcher, 'function', 'matcher should be a function on the prototype');
        // async functions have constructor name 'AsyncFunction'
        assert.strictEqual(proto.matcher.constructor.name, 'AsyncFunction', 'matcher should be declared async');
        // matcher should expect at least one argument (realCwd)
        assert.ok(proto.matcher.length >= 1, 'matcher should accept at least one parameter (realCwd)');
    });

    })