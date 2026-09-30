let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0014.extractToolResultMediaArtifact', function() {
    const mod = testpilot_subject.file_0014;
    const fn = mod.extractToolResultMediaArtifact;

    // Save originals so we can restore after tests (if present)
    let originals = {};

    beforeEach(function() {
        originals.readToolResultDetailsMedia = mod.readToolResultDetailsMedia;
        originals.collectStructuredMediaUrls = mod.collectStructuredMediaUrls;
        originals.import_parse = mod.import_parse;
    });

    afterEach(function() {
        // Restore whatever was present before
        mod.readToolResultDetailsMedia = originals.readToolResultDetailsMedia;
        mod.collectStructuredMediaUrls = originals.collectStructuredMediaUrls;
        mod.import_parse = originals.import_parse;
    });

    it('returns undefined for non-object or missing input', function() {
        assert.strictEqual(fn(null), undefined);
        assert.strictEqual(fn(undefined), undefined);
        assert.strictEqual(fn(123), undefined);
        assert.strictEqual(fn("string"), undefined);
    });

    })