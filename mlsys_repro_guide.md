# Artifact Appendix

## The OpenHands Software Agent SDK: A Composable and Extensible Foundation for Production Agents

---

### A.1 Abstract

This artifact contains the OpenHands Software Agent SDK and its companion benchmark evaluation infrastructure — together comprising the two open-source repositories needed to validate the paper's claims. The SDK is a production-ready Python framework for building AI software development agents, organized into four composable packages (SDK, Tools, Workspace, Agent Server) supporting local-to-remote deployment portability. The benchmarks repository provides standardized evaluation pipelines that pin the SDK at specific commits via a git submodule for reproducibility. The artifact enables validation of: (1) negligible event-sourcing overhead (sub-millisecond persist latency, crash recovery under 20ms), (2) the SDK's three-tier testing infrastructure, and (3) benchmark evaluation results (SWE-Bench Verified, GAIA, SWE-Bench Multimodal, SWT-Bench, Commit0) given LLM API access. All source code, tests, benchmark harnesses, and documentation are publicly available under the MIT license.

---

### A.2 Artifact Check-List (Meta-Information)

- **Algorithm:** Event-sourced state management for AI agent conversations; LLM-based tool invocation loop with action-observation cycle
- **Program:** OpenHands Software Agent SDK (Python); OpenHands Benchmarks (Python)
- **Compilation:** Python 3.12+; no compilation required (interpreted language); `uv sync` for dependency resolution (uv ≥ 0.8.13)
- **Binary:** Not applicable (pure Python packages)
- **Data set:** SWE-Bench Verified traces (433 conversations, 39,870 events) for event-sourcing benchmarks (downloadable); SWE-Bench Verified, GAIA, SWE-Bench Multimodal, SWT-Bench, and Commit0 benchmark instances (auto-fetched by evaluation harness)
- **Run-time environment:** Linux (Ubuntu 20.04+), macOS 12+, or Windows with WSL2; Docker 20.10+ for benchmark evaluation and sandbox execution
- **Hardware:** x86_64 or ARM64, 4+ CPU cores, 8 GB RAM minimum (16 GB recommended), 10 GB disk for SDK / 50+ GB for benchmark images
- **Run-time state:** Deterministic for event-sourcing benchmarks; nondeterministic for LLM-based tests and benchmarks (due to LLM inference stochasticity)
- **Execution:** Sequential for core tests; concurrent for benchmark evaluation (supports 32+ parallel workers)
- **Metrics:** Per-event persist latency (ms), crash recovery time (ms), storage per conversation (KB), system-attributable error rate (errors/1k conversations), benchmark resolution rates (%)
- **Output:** Test pass/fail reports, benchmark score JSONL files, event-sourcing latency statistics
- **Experiments:** Event-sourcing overhead benchmarks (Table 4), programmatic and integration test suites (Section 4.3), benchmark evaluations across 14 models and 5 categories (Tables 5–8)
- **How much disk space required (approximately)?:** ~10 GB for SDK + tests; ~50 GB for benchmark Docker images
- **How much time is needed to prepare workflow (approximately)?:** 5–10 minutes (SDK); 30–60 minutes (benchmarks, including Docker image builds)
- **How much time is needed to complete experiments (approximately)?:** Tier 1–2: ~10 minutes; Tier 3: ~10 minutes; Tier 4a (artifact inspection): ~30 minutes; Tier 4b (full benchmark re-execution): hours to days depending on model, benchmark, and parallelism
- **Publicly available?:** Yes
- **Code licenses (if publicly available)?:** MIT License
- **Workflow framework used?:** uv (package management), pytest (testing), custom benchmark harness with CLI entrypoints (evaluations)
- **Archived (provide DOI)?:** GitHub repositories at [https://github.com/OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) and [https://github.com/OpenHands/benchmarks](https://github.com/OpenHands/benchmarks)

---

### A.3 Description

#### A.3.1 How Delivered

The artifact is delivered as two public GitHub repositories:

| Repository | URL | Description |
|------------|-----|-------------|
| Software Agent SDK | [https://github.com/OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | SDK source code, tests, event-sourcing benchmarks, examples |
| Benchmarks | [https://github.com/OpenHands/benchmarks](https://github.com/OpenHands/benchmarks) | Evaluation infrastructure for all benchmarks in the paper |

**Additional resources:**
- **Documentation:** [https://docs.openhands.dev/sdk](https://docs.openhands.dev/sdk)
- **Benchmark Leaderboard:** [https://index.openhands.dev](https://index.openhands.dev)

The SDK repository is organized into four Python packages managed as a uv workspace:

| Package | Path | Description |
|---------|------|-------------|
| `openhands-sdk` | `openhands-sdk/` | Core abstractions: Agent, Conversation, LLM, Tool, Event system |
| `openhands-tools` | `openhands-tools/` | Concrete tool implementations (Bash, file editor, browser, etc.) |
| `openhands-workspace` | `openhands-workspace/` | Execution environments (Local, Docker, API-remote) |
| `openhands-agent-server` | `openhands-agent-server/` | REST/WebSocket API server for remote execution |

The Benchmarks repository includes evaluation pipelines for:

| Benchmark | CLI Entrypoint | Description |
|-----------|---------------|-------------|
| SWE-Bench | `swebench-infer` / `swebench-eval` | Software engineering tasks from GitHub issues |
| GAIA | `gaia-infer` / `gaia-eval` | General AI assistant tasks with multi-step reasoning |
| SWE-Bench Multimodal | `swebenchmultimodal-infer` / `swebenchmultimodal-eval` | Frontend development with multimodal inputs |
| SWT-Bench | `swtbench-infer` / `swtbench-eval` | Software testing and bug reproduction |
| Commit0 | `commit0-infer` / `commit0-eval` | Greenfield Python function implementation |

#### A.3.2 Hardware Dependencies

- **Minimum:** x86_64 or ARM64 processor, 4 CPU cores, 8 GB RAM, 10 GB disk space
- **Recommended:** 8+ CPU cores, 16 GB RAM (for Docker sandbox execution and parallel benchmark evaluation)
- **GPU:** Not required. All LLM inference is performed via remote API calls.
- **Network:** Internet access is required for LLM API calls (Tiers 3–4), Docker image pulls, and benchmark dataset downloads from HuggingFace.

#### A.3.3 Software Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | ≥ 3.12 | Runtime |
| uv | ≥ 0.8.13 | Package management ([https://docs.astral.sh/uv](https://docs.astral.sh/uv)) |
| Docker | ≥ 20.10 | Benchmark evaluation and sandbox execution |
| Git | ≥ 2.30 | Repository cloning and submodule management |

Python package dependencies are specified in `pyproject.toml` files and are automatically resolved by `uv sync`.

**LLM API Keys (for Tiers 3–4):** At least one of the following is needed for LLM-based tests:
- Anthropic API key (for Claude models)
- OpenAI API key (for GPT models)
- DeepSeek API key (for DeepSeek models)
- Tavily API key (additionally required for GAIA benchmark, which uses Tavily MCP for web search)

#### A.3.4 Data Sets

- **Event-sourcing traces:** 433 SWE-Bench Verified conversation traces (39,870 events) are downloadable from the URL specified in `scripts/event_sourcing_benchmarks/README.md` in the SDK repository. These traces are used to reproduce the event-sourcing overhead measurements reported in Table 4.
- **Benchmark instances:** SWE-Bench Verified, GAIA, SWE-Bench Multimodal, SWT-Bench, and Commit0 datasets are fetched automatically by the evaluation harness from their respective public sources (Princeton NLP, HuggingFace).

---

### A.4 Installation

#### SDK Installation (for Tiers 1–3)

```bash
# Clone the repository
git clone https://github.com/OpenHands/software-agent-sdk.git
cd software-agent-sdk

# Install uv if not already available (https://docs.astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Build the development environment (installs all packages + dev dependencies)
make build

# Verify installation
uv run python -c "from openhands.sdk import Agent, Conversation, LLM; print('SDK installed successfully')"
```

#### Benchmarks Installation (for Tier 4)

```bash
# Clone the benchmarks repository (includes SDK as a git submodule)
git clone https://github.com/OpenHands/benchmarks.git
cd benchmarks

# Initialize the SDK submodule and install all dependencies
make build

# Configure your LLM (create a JSON config file)
mkdir -p .llm_config
cat > .llm_config/my_model.json << 'EOF'
{
  "model": "anthropic/claude-sonnet-4-5-20250929",
  "api_key": "YOUR_API_KEY_HERE"
}
EOF

# Validate the configuration
uv run validate-cfg .llm_config/my_model.json
```

---

### A.5 Experiment Workflow

The experiments are organized into four tiers of increasing cost and complexity:

#### Tier 1 — Programmatic Tests (no API keys, ~5 minutes)

```bash
cd software-agent-sdk

# Run all programmatic tests (SDK, tools, cross-package)
uv run pytest tests/sdk/ tests/tools/ tests/cross/ -v
```

These tests verify core SDK logic, event system, state management, tool contracts, and API interfaces using mocked LLM responses. All tests should pass.

#### Tier 2 — Event-Sourcing Benchmarks (no API keys, ~5 minutes)

```bash
cd software-agent-sdk/scripts/event_sourcing_benchmarks

# Step 1: Download the evaluation traces (433 SWE-Bench conversations)
curl -L -o results.tar.gz \
  https://results.eval.all-hands.dev/swtbench/litellm_proxy-jade-spark-2862/21870831025/results.tar.gz
tar xzf results.tar.gz

# Step 2: Run the three benchmark scripts
# (replace <path> with the extracted run directory containing conversations/ and output.jsonl)

# Persist latency per event / action cycle (reproduces Table 4, rows 1–2)
uv run python bench_persist_latency.py --eval-dir <path>

# Replay time vs. log size and time-to-recover (reproduces Table 4, rows 3–4)
uv run python bench_replay_and_recovery.py --eval-dir <path>

# Storage growth and composition (reproduces Table 4, row 5)
uv run python bench_storage_growth.py --eval-dir <path>
```

#### Tier 3 — LLM Integration Tests (requires API keys, ~5 minutes, ~$3)

```bash
cd software-agent-sdk

# Set API key for your preferred provider
export ANTHROPIC_API_KEY="your-key-here"
# or: export OPENAI_API_KEY="your-key-here"

# Run integration tests (real LLM calls)
uv run pytest tests/integration/ -v

# Run example validation (ensures all SDK examples work end-to-end)
uv run pytest tests/examples/ -v
```

These tests exercise real agent-LLM interactions including tool invocation, file manipulation, command execution, and multi-step reasoning.

**Evaluators are also encouraged to check the SDK's public CI directly**, which continuously validates the testing infrastructure described in Section 4.3:

- **Unit tests** (run on every commit): [github.com/OpenHands/software-agent-sdk/actions/workflows/tests.yml](https://github.com/OpenHands/software-agent-sdk/actions/workflows/tests.yml)
- **Integration tests** (run nightly across multiple models): [github.com/OpenHands/software-agent-sdk/actions/workflows/integration-runner.yml](https://github.com/OpenHands/software-agent-sdk/actions/workflows/integration-runner.yml)
- **Example tests** (run periodically): [github.com/OpenHands/software-agent-sdk/actions/workflows/run-examples.yml](https://github.com/OpenHands/software-agent-sdk/actions/workflows/run-examples.yml)
- **Integration test results tracker** (pass rates, costs, and links to detailed agent logs): [github.com/OpenHands/software-agent-sdk/issues/2078](https://github.com/OpenHands/software-agent-sdk/issues/2078)
- **Example test results tracker** (per-example status, duration, and cost): [github.com/OpenHands/software-agent-sdk/issues/976](https://github.com/OpenHands/software-agent-sdk/issues/976)

Each workflow run includes full logs, and the nightly tracker issue aggregates results with per-model breakdowns. This provides an independent, continuously-updated record of the SDK's testing methodology in action — no API keys required to inspect.

#### Tier 4a — Benchmark Artifact Inspection (no API keys needed)

Evaluation artifacts (logs, agent traces, per-instance outputs) for all benchmark runs reported in the paper are publicly available on the OpenHands Index:

1. Visit [https://index.openhands.dev](https://index.openhands.dev)
2. Locate the model and benchmark run in the leaderboard table
3. Click the ⬇️ download links in the **Logs** column to download evaluation artifacts for each benchmark category
4. Artifacts include per-instance JSONL output files, agent conversation traces, and evaluation scores

This allows evaluators to verify reported results (Tables 5–8) by inspecting the actual evaluation outputs without re-running experiments.

#### Tier 4b — Full Benchmark Re-execution (requires API keys + Docker, hours, $100–$1000)

```bash
cd benchmarks

# --- SWE-Bench Verified ---
# Step 1: Build Docker images for SWE-Bench instances
uv run python -m benchmarks.swebench.build_images \
  --dataset princeton-nlp/SWE-bench_Verified \
  --split test \
  --image ghcr.io/openhands/eval-agent-server \
  --target source-minimal

# Step 2: Run inference
uv run swebench-infer .llm_config/my_model.json \
  --dataset princeton-nlp/SWE-bench_Verified \
  --split test \
  --workspace docker \
  --max-iterations 100

# Step 3: Evaluate
uv run swebench-eval output.jsonl

# --- GAIA ---
TAVILY_API_KEY=xxx uv run gaia-infer .llm_config/my_model.json \
  --level 2023_all \
  --split validation
uv run python -m benchmarks.gaia.get_score --file outputs/gaia/output.jsonl
```

See the individual benchmark directories in the [Benchmarks repository](https://github.com/OpenHands/benchmarks) for detailed instructions for each benchmark (SWE-Bench Verified, GAIA, SWE-Bench Multimodal, SWT-Bench, Commit0).

---

### A.6 Evaluation and Expected Results

#### Tier 1: Programmatic Tests
- **Expected:** All tests pass (100% pass rate)
- **Validates:** Core SDK logic, event system correctness, state management, tool interfaces (Sections 3.1–3.8)

#### Tier 2: Event-Sourcing Benchmarks (Table 4)
- **Expected results:**

| Metric | Expected (Median) | Expected (P95) | Expected (Max, 358 events) |
|--------|-------------------|-----------------|---------------------------|
| Per-event persist latency | ~0.17 ms | ~0.27 ms | — |
| Action cycle persist (Action+Obs) | ~0.36 ms | — | — |
| Full state replay | ~2.3 ms | — | < 10 ms |
| Crash recovery | ~5 ms | — | < 20 ms |
| Storage per conversation | ~380 KB | — | ~3.4 MB |

- **Tolerance:** Results may vary by ±30% depending on disk I/O performance of the host machine. The key claim — that all latencies are negligible relative to LLM round-trip times (1–30s) — should hold on any reasonable hardware.
- **Validates:** Section 4.2, Table 4

#### Tier 3: Integration Tests
- **Expected:** Majority of tests pass. Occasional failures due to LLM nondeterminism are expected (typically < 10% failure rate). Historic nightly CI results are publicly visible at [github.com/OpenHands/software-agent-sdk/issues/2078](https://github.com/OpenHands/software-agent-sdk/issues/2078) for reference.
- **Validates:** Testing methodology described in Section 4.3, Figure 4

#### Tier 4a: Benchmark Artifact Inspection
- **Expected:** Downloaded evaluation artifacts (logs, traces, per-instance outputs) should match the aggregate scores reported in Tables 5–8. Evaluators can verify individual instance results and inspect agent behavior via conversation traces.
- **Validates:** Section 4.4, Tables 5–8

#### Tier 4b: Benchmark Re-execution (Tables 5–8)
- **Expected:** Results within statistical variance of reported numbers. Exact values may shift due to LLM provider API versioning and model updates between the paper's evaluation date and the review period.
- **Key results to verify:**
  - SWE-Bench Verified with Claude Sonnet 4.5: ~72.8% (Table 6)
  - GAIA (val) with Claude Sonnet 4: ~57.6% (Table 6)
  - State-of-the-art performance on SWE-Bench Multimodal, Commit0, and GAIA (Table 8)
- **Validates:** Section 4.4, Tables 5–8

---

### A.7 Experiment Customization

- **Model selection:** Any of the 100+ models supported via LiteLLM can be used. Configure models via a JSON file (see benchmarks `README.md`). Examples: `anthropic/claude-sonnet-4-5-20250929`, `openai/gpt-5`, `deepseek/deepseek-chat`.
- **Custom tools:** Create new tools by subclassing `Tool` and registering them. See `examples/01_standalone_sdk/` for patterns (custom tools, MCP integration, skills, etc.).
- **Workspace modes:** Switch between local execution (`LocalWorkspace`) and Docker sandbox (`DockerWorkspace`) by changing the workspace parameter (see Figure 5 in the paper).
- **Benchmark parallelism:** Adjust `--num-workers` in benchmark commands to control parallelism (Docker workspace limited by local resources; remote workspace supports 32+ workers).
- **Security policies:** Configure custom `SecurityAnalyzer` and `ConfirmationPolicy` for different risk tolerance levels.
- **Context management:** Swap or compose different condensation strategies via the `PipelineCondenser`.
- **SDK version pinning:** The benchmarks repo pins the SDK at a specific commit via a git submodule (`vendor/software-agent-sdk/`). Update the submodule to evaluate different SDK versions.
