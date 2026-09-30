let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.buildApprovalPendingMessage', function() {

    it('builds a correct message with minimal params (no warningText)', function() {
        const params = {
            approvalSlug: 'abc123',
            approvalId: 'full-id-0001',
            host: 'host.example.com',
            nodeId: 'node-42',
            cwd: '/home/user',
            command: 'echo hello'
            // warningText omitted
        };

        const actual = testpilot_subject.file_0008.buildApprovalPendingMessage(params);

        const fence = '```';
        const commandBlock = `${fence}sh\n${params.command}\n${fence}`;

        const expectedLines = [
            `Approval required (id ${params.approvalSlug}, full ${params.approvalId}).`,
            `Host: ${params.host}`,
            `Node: ${params.nodeId}`,
            `CWD: ${params.cwd}`,
            `Command:`,
            commandBlock,
            "Mode: foreground (interactive approvals available).",
            "Background mode requires pre-approved policy (allow-always or ask=off).",
            `Reply with: /approve ${params.approvalSlug} allow-once|allow-always|deny`,
            "If the short code is ambiguous, use the full id in /approve."
        ];
        const expected = expectedLines.join("\n");

        assert.strictEqual(actual, expected);
    });

    })