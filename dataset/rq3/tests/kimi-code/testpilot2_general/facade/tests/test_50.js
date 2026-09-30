let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.invalidate', function() {
    // Helper to get the prototype and its parent prototype
    function getPrototypes() {
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        const parentProto = Object.getPrototypeOf(proto);
        return { proto, parentProto };
    }

    it('calls headerText.setText with buildHeader result, then rebuildBody, then parent.invalidate (order)', function() {
        const { proto, parentProto } = getPrototypes();

        // Save original parent method so we can restore it
        const originalParentInvalidate = parentProto.invalidate;

        // Sequence recorder
        const seq = [];

        // Spy parent invalidate
        parentProto.invalidate = function() {
            seq.push('parent');
            // no return value
        };

        // Create a fake "this" for calling the prototype method
        const fakeThis = {
            headerText: {
                setText: function(arg) {
                    seq.push('setText:' + arg);
                }
            },
            buildHeader: function() {
                seq.push('buildHeader');
                return 'THE_HEADER';
            },
            rebuildBody: function() {
                seq.push('rebuildBody');
            }
        };

        try {
            // Call the class method (super will resolve against the method's home object)
            proto.invalidate.call(fakeThis);

            // Validate sequence and arguments
            assert.deepStrictEqual(
                seq,
                ['buildHeader', 'setText:THE_HEADER', 'rebuildBody', 'parent'],
                'Expected buildHeader -> headerText.setText -> rebuildBody -> parent.invalidate order with correct arg'
            );
        } finally {
            // Restore original parent invalidate
            parentProto.invalidate = originalParentInvalidate;
        }
    });

    })