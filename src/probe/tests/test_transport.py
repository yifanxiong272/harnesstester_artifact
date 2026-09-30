"""Local HTTP/HTTPS/proxy checks for the TypeScript model transport."""

from __future__ import annotations

import json
import os
import select
import socket
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def certificate(tmp_path_factory):
    root = tmp_path_factory.mktemp("probe-tls")
    cert, key = root / "cert.pem", root / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return cert, key


@pytest.mark.parametrize("scheme", ["https", "http"])
@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("scenario", ["chunked", "retry", "nonretry", "timeout"])
def test_model_transport_matches_formal(certificate, scheme, proxy, scenario):
    root = os.environ.get("PROBE_FORMAL_ROOT")
    modules = [Path(__file__).resolve().parents[1] / "typescript/run/client.mjs"]
    if root and scheme == "https":
        modules.append(Path(root) / "src/common/test_augment/TS/run/client.mjs")
    cert, key = certificate
    results = []
    for module in modules:
        requests, connections = [], []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_POST(self):
                requests.append(
                    json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                )
                assert self.headers["Authorization"] == "Bearer local-fixture-key"
                if scenario == "timeout":
                    self.close_connection = True
                    self.rfile.read(1)
                    return
                status = (
                    400
                    if scenario == "nonretry"
                    else 429
                    if scenario == "retry" and len(requests) == 1
                    else 200
                )
                payload = (
                    {"choices": [{"message": {"content": "fixture"}}]}
                    if status == 200
                    else {"error": "local-fixture-key"}
                )
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                self.send_header("Retry-After", "0.001")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for chunk in (body[:7], body[7:]):
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        if scheme == "https":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)

        class Proxy(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_CONNECT(self):
                connections.append((self.path, self.headers.get("Proxy-Authorization")))
                assert self.path == f"localhost:{server.server_port}"
                with socket.create_connection(
                    ("127.0.0.1", server.server_port)
                ) as upstream:
                    self.send_response(200)
                    self.end_headers()
                    while True:
                        readable, _, _ = select.select(
                            [self.connection, upstream], [], [], 5
                        )
                        if not readable:
                            return
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                return
                            (
                                upstream
                                if source is self.connection
                                else self.connection
                            ).sendall(data)

        proxy_server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        servers = (server, proxy_server)
        threads = [
            threading.Thread(target=s.serve_forever, daemon=True) for s in servers
        ]
        for thread in threads:
            thread.start()
        try:
            env = {
                key: value
                for key, value in os.environ.items()
                if "PROXY" not in key.upper() and key != "NODE_TLS_REJECT_UNAUTHORIZED"
            }
            env["NODE_EXTRA_CA_CERTS"] = str(cert)
            settings = {
                "OPENAI_API_KEY": "local-fixture-key",
                "OPENAI_BASE_URL": f"{scheme}://localhost:{server.server_port}/v1",
                "LLM_MAX_TOKENS": "17",
            }
            if proxy:
                proxy_key = "TEST_AUGMENT_HTTPS_PROXY" if scheme == "https" else "HTTPS_PROXY"
                settings[proxy_key] = (
                    f"http://user:pass@127.0.0.1:{proxy_server.server_port}"
                )
            script = """
                const { chatCompletion } = await import(process.argv[1]);
                try {
                  const result = await chatCompletion({
                    prompt: 'fixture prompt', model: 'fixture', provider: 'openai',
                    env: JSON.parse(process.argv[2]), timeoutMs: 300,
                    retries: Number(process.argv[3]),
                  });
                  console.log(JSON.stringify({result}));
                } catch (error) {
                  console.log(JSON.stringify({error: error.message, retryable: error.retryable}));
                }
            """
            completed = subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    script,
                    module.as_uri(),
                    json.dumps(settings),
                    "1" if scenario == "retry" else "0",
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert completed.returncode == 0, completed.stderr
            response = json.loads(completed.stdout)
            assert len(requests) == (2 if scenario == "retry" else 1)
            assert all(r["max_completion_tokens"] == 17 for r in requests)
            if scenario in {"chunked", "retry"}:
                assert (
                    response["result"]["choices"][0]["message"]["content"] == "fixture"
                )
            elif scenario == "timeout":
                assert "timed out" in response["error"]
            else:
                assert response["retryable"] is False
                assert "local-fixture-key" not in response["error"]
            if proxy and scheme == "https":
                assert len(connections) == len(requests)
                assert all(auth == "Basic dXNlcjpwYXNz" for _, auth in connections)
            else:
                assert not connections
            results.append((requests, response))
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join()
    assert all(result == results[0] for result in results)


def test_http_transport_defaults_to_port_80():
    module = Path(__file__).resolve().parents[1] / "typescript/run/client.mjs"
    script = """
        import assert from 'node:assert/strict';
        import http from 'node:http';
        import https from 'node:https';
        import { EventEmitter } from 'node:events';
        const { chatCompletion } = await import(process.argv[1]);
        let captured;
        http.request = (options) => {
          captured = options;
          const request = new EventEmitter();
          request.destroy = () => {};
          request.end = () => request.emit('error', new Error('intercepted HTTP request'));
          return request;
        };
        https.request = () => { throw new Error('unexpected HTTPS request'); };
        await assert.rejects(chatCompletion({
          prompt: 'fixture prompt', model: 'fixture', provider: 'openai',
          env: {
            OPENAI_API_KEY: 'local-fixture-key',
            OPENAI_BASE_URL: 'http://localhost/v1',
            HTTPS_PROXY: 'not a valid proxy URL',
          },
          timeoutMs: 300, retries: 0,
        }), /intercepted HTTP request/);
        assert.equal(captured.port, 80);
        assert.equal(captured.path, '/v1/chat/completions');
        assert.ok(captured.agent instanceof http.Agent);
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, module.as_uri()],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
