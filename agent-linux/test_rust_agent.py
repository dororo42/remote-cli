"""The Rust agent, held to the same end-to-end contract as the Python one: the real relay
runs as a subprocess, this test speaks the viewer protocol, and the binary under test is
agent-rust/target/release/remote-cli-agent. Build it first:

    cargo build --release --manifest-path ../agent-rust/Cargo.toml
"""
import os
import unittest

import test_agent

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "..", "agent-rust", "target", "release", "remote-cli-agent")


@unittest.skipUnless(os.path.isfile(BINARY), "build the Rust agent first: cargo build --release (agent-rust/)")
class RustAgentContract(test_agent.EndToEnd):
    """Inherits the full e2e flow; only the binary under test changes."""

    @classmethod
    def agent_command(cls, agent_data):
        return [BINARY, "--data", agent_data]


if __name__ == "__main__":
    unittest.main()
