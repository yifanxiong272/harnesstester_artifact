let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to build a very permissive mock "shell" object.
    // The mock tries to be flexible to match several common shell APIs:
    // - shell.exec(cmd) returning a Promise-like (thenable) resolving to { code, stdout, stderr }
    // - shell.test('-f', path) returning a boolean or Promise<boolean>
    // - shell.stat / shell.lstat returning resolved stat-like object or rejected error
    // - shell.exists / shell.pathExists calling a callback or returning a boolean/thenable
    // - shell.readFile / shell.access
    //
    // The mock inspects the arguments to detect the binary name (binName) and will
    // behave as if a completion file exists when `exists === true` and not otherwise.
    function buildMockShell(exists, binName = 'openclaw') {
        function containsBinName(args) {
            try {
                return args.join(' ').indexOf(binName) !== -1;
            } catch (e) {
                return false;
            }
        }

        function makeThenable(value) {
            return {
                value: value,
                then: function(resolve) {
                    // resolve asynchronously to mimic real async behavior
                    setImmediate(() => resolve(value));
                }
            };
        }

        const handler = {
            get: function(target, prop) {
                // Return a function for any method access
                return function(...args) {
                    // detect callback style
                    let cb = null;
                    if (args.length && typeof args[args.length - 1] === 'function') {
                        cb = args.pop();
                    }

                    const askedAboutBin = containsBinName(args);

                    // Behavior for various common method names
                    if (prop === 'exec' || prop === 'run' || prop === 'spawn') {
                        // Many implementations look at exit/code or stdout content
                        const result = {
                            code: (askedAboutBin ? (exists ? 0 : 1) : (exists ? 0 : 1)),
                            stdout: askedAboutBin ? (exists ? '/some/path/' + binName + '\n' : '') : '',
                            stderr: ''
                        };
                        if (cb) cb(null, result);
                        return makeThenable(result);
                    }

                    if (prop === 'test') {
                        // shell.test('-f', path) may be used and return boolean
                        const result = !!askedAboutBin && exists;
                        if (cb) cb(null, result);
                        // return boolean synchronously or a thenable (both supported)
                        // Return boolean so sync usage works; if Promise-style expected,
                        // the caller can handle a thenable too; to be safe also return thenable
                        // if user awaits the result (we return a thenable-like object with truthy boolean)
                        const thenable = makeThenable(result);
                        // attach primitive boolean too for synchronous checks
                        thenable.valueOf = () => result;
                        return thenable;
                    }

                    if (prop === 'exists' || prop === 'pathExists') {
                        const result = !!askedAboutBin && exists;
                        if (cb) cb(null, result);
                        return makeThenable(result);
                    }

                    if (prop === 'stat' || prop === 'lstat') {
                        if (askedAboutBin && exists) {
                            const statLike = { isFile: () => true };
                            if (cb) cb(null, statLike);
                            return makeThenable(statLike);
                        } else {
                            const err = new Error('ENOENT');
                            err.code = 'ENOENT';
                            if (cb) cb(err);
                            // simulate a rejected promise
                            return {
                                then: function(_, reject) {
                                    setImmediate(() => reject(err));
                                }
                            };
                        }
                    }

                    if (prop === 'readFile' || prop === 'cat') {
                        if (askedAboutBin && exists) {
                            if (cb) cb(null, 'contents');
                            return makeThenable('contents');
                        } else {
                            const err = new Error('ENOENT');
                            err.code = 'ENOENT';
                            if (cb) cb(err);
                            return {
                                then: function(_, reject) {
                                    setImmediate(() => reject(err));
                                }
                            };
                        }
                    }

                    if (prop === 'access') {
                        if (askedAboutBin && exists) {
                            if (cb) cb(null);
                            return makeThenable(true);
                        } else {
                            const err = new Error('ENOENT');
                            err.code = 'ENOENT';
                            if (cb) cb(err);
                            return {
                                then: function(_, reject) {
                                    setImmediate(() => reject(err));
                                }
                            };
                        }
                    }

                    // Default: return something truthy/falsy based on askedAboutBin
                    const defaultRes = !!askedAboutBin && exists;
                    if (cb) cb(null, defaultRes);
                    return makeThenable(defaultRes);
                };
            }
        };

        return new Proxy({}, handler);
    }

    it('should resolve to true when completion cache exists for given binary (mocked)', async function() {
        const shell = buildMockShell(true, 'openclaw');
        const result = await testpilot_subject.file_0015.completionCacheExists(shell, 'openclaw');
        assert.strictEqual(result, true, 'Expected completionCacheExists to resolve to true when cache exists');
    });

    })