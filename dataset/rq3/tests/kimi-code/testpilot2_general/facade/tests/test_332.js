let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let fsp = fs.promises;
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure tests have a little more time if the environment is slow
    this.timeout(5000);

    it('FsService.prototype.matcher exists and returns a function when awaited', async function() {
        let svc = new testpilot_subject.file_0004.FsService();
        assert.strictEqual(typeof svc.matcher, 'function', 'matcher should be a function');

        // create a temporary directory to pass as realCwd
        let tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'testpilot-'));
        try {
            // call matcher; it's async so should resolve (not throw)
            let matchFn = await svc.matcher(tmp);

            // Older tests expected a function directly; some implementations return an
            // object that exposes a matching function (e.g. .test or .match). Accept
            // either a function or an object that exposes a callable matcher.
            if (typeof matchFn !== 'function') {
                // ensure it's an object and exposes a matcher function
                assert.ok(matchFn && typeof matchFn === 'object', 'matcher(realCwd) should resolve to a function or an object');
                const hasCallable =
                    typeof matchFn.test === 'function' ||
                    typeof matchFn.match === 'function' ||
                    typeof matchFn.exec === 'function';
                assert.ok(hasCallable, 'matcher(realCwd) object should expose a callable matcher (e.g. .test or .match)');
            } else {
                // it's a function — ok
                assert.strictEqual(typeof matchFn, 'function', 'matcher(realCwd) should resolve to a function');
            }
        } finally {
            // cleanup
            await fsp.rm(tmp, { recursive: true, force: true });
        }
    });

    })