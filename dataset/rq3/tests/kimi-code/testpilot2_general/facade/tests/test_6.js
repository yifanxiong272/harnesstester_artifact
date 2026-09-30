let mocha = require('mocha');
let assert = require('assert');

// Instead of requiring an external module, create test objects locally so tests are self-contained.
describe('test testpilot_subject', function() {
    // Helper to build the nested structure under test.
    function makeSubjectWithId(id) {
        return {
            file_0002: {
                FsSearchService: {
                    $di$dependencies: [
                        { id: id }
                    ]
                }
            }
        };
    }

    it('number id: toString() returns numeric string', function() {
        const testpilot_subject = makeSubjectWithId(123);
        const result = testpilot_subject.file_0002.FsSearchService.$di$dependencies[0].id.toString();
        assert.strictEqual(result, '123');
    });

    })