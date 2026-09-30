let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0009.CodeIndexSearchService.prototype.searchIndex', function() {
        it('should exist as a function on the prototype and have arity 2', function() {
            if (!testpilot_subject || !testpilot_subject.file_0009) {
                this.skip(); // module not present in this environment
                return;
            }
            let Svc = testpilot_subject.file_0009.CodeIndexSearchService;
            if (!Svc) {
                this.skip();
                return;
            }
            assert.strictEqual(typeof Svc.prototype.searchIndex, 'function', 'searchIndex should be a function on the prototype');
            // Expect the declared parameter count to be 2 (query, directoryPrefix)
            assert.strictEqual(Svc.prototype.searchIndex.length, 2, 'searchIndex should declare two parameters');
        });

            })
})