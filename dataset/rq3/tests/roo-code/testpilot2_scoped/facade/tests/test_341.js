let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('TagMatcher constructor exists and is constructible', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(typeof testpilot_subject.file_0014 === 'object' || typeof testpilot_subject.file_0014 === 'function',
                  'module should expose file_0014');
        let TagMatcher = testpilot_subject.file_0014 && testpilot_subject.file_0014.TagMatcher;
        assert.ok(typeof TagMatcher === 'function', 'TagMatcher should be a function/class');

        // Construct with minimal arguments and ensure it doesn't throw and returns an object
        let inst = new TagMatcher('mytag', null);
        assert.ok(inst && (typeof inst === 'object' || typeof inst === 'function'),
                  'constructing TagMatcher should produce an object-like instance');
    });

    })