let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals so we can restore after tests
    const orig = {};
    beforeEach(function() {
        const mod = testpilot_subject.file_0015;
        // Save any existing properties we will override
        ['getShellProfilePath','resolveCompletionCachePath','isCompletionProfileHeader','isCompletionProfileLine','import_utils','import_promises'].forEach(k=>{
            orig[k] = mod.hasOwnProperty(k) ? mod[k] : undefined;
        });
    });
    afterEach(function() {
        const mod = testpilot_subject.file_0015;
        // Restore originals (or delete if they didn't exist before)
        ['getShellProfilePath','resolveCompletionCachePath','isCompletionProfileHeader','isCompletionProfileLine','import_utils','import_promises'].forEach(k=>{
            if (typeof orig[k] === 'undefined') {
                try { delete mod[k]; } catch(e) { mod[k] = undefined; }
            } else {
                mod[k] = orig[k];
            }
        });
    });

    it('returns false when the profile path does not exist', async function() {
        const mod = testpilot_subject.file_0015;

        const profilePath = '/nonexistent/profile/path';
        // mock helpers
        mod.getShellProfilePath = (shell) => profilePath;
        // pathExists: profile does not exist
        mod.import_utils = {
            pathExists: async (p) => {
                return false; // no path exists
            }
        };
        // readFile should not be called, but provide anyway
        mod.import_promises = { default: { readFile: async () => 'irrelevant' } };
        // these won't be needed but supply
        mod.resolveCompletionCachePath = () => '/some/cache';
        mod.isCompletionProfileHeader = () => false;
        mod.isCompletionProfileLine = () => false;

        const res = await mod.isCompletionInstalled('bash','openclaw');
        assert.strictEqual(res, false);
    });

    })