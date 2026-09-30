let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ORIGINAL_ENV = process.env.NODE_ENV;
    const ORIGINAL_CONSOLE = global.console;
    let capturedConsole;
    let fakeWindow;
    let fakeDocument;
    let originalFetch;

    // Helper to create a fresh fake DOM environment per test
    function setupFakeDOM({ scripts = [], fetchImpl = null } = {}) {
        // capture console calls
        capturedConsole = {
            log: [],
            error: [],
            debug: []
        };
        global.console = {
            log: (...args) => capturedConsole.log.push(args),
            error: (...args) => capturedConsole.error.push(args),
            debug: (...args) => capturedConsole.debug.push(args)
        };

        // simple event listener store
        const listeners = {};

        fakeWindow = {
            addEventListener: (type, fn) => {
                listeners[type] = listeners[type] || [];
                listeners[type].push(fn);
            },
            // helper to dispatch events for tests
            _dispatchEvent: async (type, event) => {
                const fns = listeners[type] || [];
                // Call handlers sequentially and await any returned promises
                for (const fn of fns) {
                    try {
                        // handlers may be async
                        await fn(event);
                    } catch (e) {
                        // swallow; handlers should handle their own errors
                    }
                }
            }
        };

        // simple document implementation
        const appended = [];
        fakeDocument = {
            head: {
                appendChild: (el) => {
                    appended.push(el);
                    return el;
                }
            },
            createElement: (name) => {
                // only 'link' is used by the function under test
                if (name === 'link') {
                    return { rel: null, as: null, href: null, crossOrigin: null };
                }
                // fallback
                return {};
            },
            getElementsByTagName: (name) => {
                if (name === 'script') {
                    // return a plain array (the function under test iterates with for loop)
                    return scripts;
                }
                return [];
            },
            // for tests: allow inspection
            _appended: appended
        };

        // Provide fetch (global) - the function under test calls global fetch
        originalFetch = global.fetch;
        if (fetchImpl) {
            global.fetch = fetchImpl;
        } else {
            // default: return a rejected promise so inline sourceMappingURL handling is skipped
            global.fetch = () => Promise.reject(new Error('no fetch'));
        }

        // attach to globals
        global.window = fakeWindow;
        global.document = fakeDocument;
    }

    function teardownFakeDOM() {
        // restore console, fetch, window, document
        global.console = ORIGINAL_CONSOLE;
        global.fetch = originalFetch;
        delete global.window;
        delete global.document;
    }

    beforeEach(function() {
        // ensure production mode so the function proceeds
        process.env.NODE_ENV = 'production';
    });

    afterEach(function() {
        process.env.NODE_ENV = ORIGINAL_ENV;
        teardownFakeDOM();
    });

    it('creates preload links for possible source map urls for scripts with src', function() {
        // Prepare one script with src
        const scriptSrc = 'https://cdn.example.com/assets/app.js';
        setupFakeDOM({
            scripts: [{ src: scriptSrc }],
            // fetch rejects to skip inline sourceMappingURL handling
            fetchImpl: () => Promise.reject(new Error('fetch disabled for test'))
        });

        // Invoke
        testpilot_subject.file_0005.initializeSourceMaps();

        // Immediately, the code should have appended preload links for the possibleMapUrls
        const appended = fakeDocument._appended;
        // Expect 5 preloads per script for the initial possibleMapUrls
        assert.strictEqual(appended.length, 5, 'Should append 5 preload links for possible map URLs');

        const expected = [
            `${scriptSrc}.map`,
            `${scriptSrc}?source-map=true`,
            scriptSrc.replace(/\.js$/, ".js.map"),
            scriptSrc.replace(/\.js$/, ".map.json"),
            scriptSrc.replace(/\.js$/, ".sourcemap")
        ];
        const hrefs = appended.map(el => el.href);
        assert.deepStrictEqual(hrefs, expected);
    });

    })