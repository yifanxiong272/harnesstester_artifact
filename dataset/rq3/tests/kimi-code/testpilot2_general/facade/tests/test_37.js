let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs');
const path = require('path');
const os = require('os');

describe('test testpilot_subject', function() {
    // Create temp directories/files per test to avoid external dependencies
    let tmpDir;
    beforeEach(function() {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'grep-test-'));
    });
    afterEach(function() {
        try {
            // Node 12+ supports recursive rm; fallback to rmdirSync if necessary
            fs.rmSync(tmpDir, { recursive: true, force: true });
        } catch (e) {
            // best-effort cleanup
            try {
                const rimraf = require('rimraf');
                rimraf.sync(tmpDir);
            } catch (_) {}
        }
    });

    // Helper to write files
    function writeFile(relPath, content) {
        const abs = path.join(tmpDir, relPath);
        const dir = path.dirname(abs);
        fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(abs, content, 'utf8');
    }

    // Create a service-like object that uses the real prototype method but supplies
    // its own walk() and matcher() so tests are self-contained.
    function makeService() {
        // Create object that uses the real prototype method
        const svc = Object.create(testpilot_subject.file_0002.FsSearchService.prototype);
        // Implement a walk that recursively yields files under cwd
        svc.walk = async function(cwd, _base, matcher, cb) {
            async function walkDir(relBase) {
                const abs = path.join(cwd, relBase);
                let entries;
                try {
                    entries = await fs.promises.readdir(abs, { withFileTypes: true });
                } catch (e) {
                    return;
                }
                for (const ent of entries) {
                    const rel = relBase ? path.join(relBase, ent.name) : ent.name;
                    const entAbs = path.join(cwd, rel);
                    if (ent.isDirectory()) {
                        await walkDir(rel);
                    } else if (ent.isFile()) {
                        // If a matcher was provided, emulate that the walk passes paths to it.
                        // The original matcher likely returns true for ignored files; our matcher
                        // is expected to return false for not-ignored.
                        if (matcher) {
                            // matcher may be synchronous or asynchronous
                            const skip = await matcher(rel);
                            if (skip) continue;
                        }
                        await cb(rel, ent.name, 'file');
                    }
                }
            }
            await walkDir('');
        };
        // Provide a default matcher (no files ignored)
        svc.matcher = async function(_cwd) {
            return async function(/*rel*/) {
                return false;
            };
        };
        return svc;
    }

    it('finds matches across multiple files and returns correct metadata', async function() {
        // Arrange: create files
        writeFile('a.txt', 'first line\nneedle in line\nlast');
        writeFile('sub/b.txt', 'needle here\nanother line\nneedle again');

        const svc = makeService();

        const req = {
            // Use a string pattern instead of a RegExp to avoid issues in implementations
            // that expect a string and call .replace on the pattern.
            pattern: 'needle',
            follow_gitignore: false,
            include_globs: null,
            exclude_globs: null,
            max_files: 10,
            max_matches_per_file: 10,
            max_total_matches: 100,
            context_lines: 1
        };

        const signal = { aborted: false };
        const startedAt = Date.now();

        // Act
        const res = await svc.grepWithNode(tmpDir, req, signal, startedAt);

        // Assert
        assert.ok(res.files && Array.isArray(res.files), 'files array returned');
        // should see matches in both files
        const paths = res.files.map(f => f.path).sort();
        assert.deepStrictEqual(paths, ['a.txt', path.join('sub', 'b.txt')].sort());
        // Check number of matches aggregated
        const totalMatches = res.files.reduce((acc, f) => acc + (f.matches ? f.matches.length : 0), 0);
        assert.strictEqual(totalMatches, 3);
        assert.strictEqual(res.files_scanned, 2);
        assert.strictEqual(res.truncated, false);
        assert.ok(typeof res.elapsed_ms === 'number' && res.elapsed_ms >= 0);
        // Validate a match shape
        const aMatch = res.files.find(f => f.path === 'a.txt').matches[0];
        assert.strictEqual(aMatch.line, 2);
        assert.strictEqual(aMatch.text.includes('needle'), true);
        assert.ok(Array.isArray(aMatch.before) && Array.isArray(aMatch.after));
    });

    })