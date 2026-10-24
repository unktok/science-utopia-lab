# Baseline run: Qwen3-8B / Ollama / Apple Silicon

## Identity

- Date: 2026-10-24
- Status: complete
- Purpose: ローカル実モデル経路と年次 simulation の end-to-end smoke test
- Run ID: `explore_smoke_qwen3_8b_neutral_i2_n10_y1_seed42_costv1_per_paper_resub5_ledger1_acdad001284e`

## Environment

- Hardware: Apple M5 Pro, unified memory 64 GB
- OS: macOS 27.0.1 (26A434), arm64
- Python: uv-managed CPython 3.11.15
- Ollama: 0.33.3
- Model: `qwen3:8b`
- Observed model residency: 11 GB, 100% GPU in `ollama ps`
- PyTorch: 2.9.0
- NumPy: 2.4.6
- SciPy: 1.17.1
- RAG device: CPU

## Configuration

- Experiment: `exploration_vs_exploitation`, stage `smoke`
- Institutions: 2
- Researchers per institution: 5
- Total researchers: 10
- Years: 1
- Conferences: 1
- Seed: 42
- LLM batch size: 2
- Dataset: `Ahren09/SciEvo`, configuration `arxiv`
- Dataset revision: `f80fb38a034b2f763dfcbdd2cd187f5b42ddcce6`
- Start year: 2016
- Filtered retrieval corpus: 14,726 CS papers

## Command

```bash
scripts/run_macos_ollama.sh
```

## Results

- Wall-clock: approximately 27 minutes
- Researchers: 10
- Active researchers: 10
- Cumulative unique papers: 5
- Accepted papers: 2
- Submission attempts: 5
- Peer reviews: 15
- Total resources after year 1: 1020.0
- Reconciled resource-ledger rows: 10
- Checkpoint: `outputs/checkpoints/<RUN_ID>/checkpoint_year_1.json`
- Numerical report: `outputs/docs/macos-quickstart-report/report.json`

## Evidence hashes

- Run manifest SHA-256: `639fc187666e77189a3bab228f65a72f4b5839bcee5b5cfec4aa8d6cc3b30cc1`
- Year-1 checkpoint SHA-256: `d2d1e0beb955a142167571aa625a9fc84a096c0a70487bb81e3046db6eb27b42`

## Deviations and limitations

- 論文の本番 Linux/vLLM campaign ではなく、Ollama のOpenAI互換APIを使用。
- Qwen3-8B はローカル開発用であり、大規模モデル条件と数値的に同一ではない。
- Ollama tag は immutable な Hugging Face tokenizer revision ではないため、vLLM固有の exact-token request audit は省略。
- 1 seed、1年、10研究者なので科学的効果の推定には使えない。これは実行可能性と計測経路の確認である。
- RAG のMPS実行は高水位メモリエラーのため採用せず、CPUでembedding indexを構築・利用した。

## Interpretation

ローカルで制度探索を開発するための最小実モデル基盤は成立した。次のボトルネックはモデルを載せることではなく、約27分/runの計算費用、確率性の推定、設計変数と目的指標の形式化である。

