#!/bin/zsh
set -euo pipefail

repo_dir=${0:A:h:h}
cd "$repo_dir"

model=${SCIENCEUTOPIA_MODEL:-qwen3:8b}
endpoint=${SCIENCEUTOPIA_OLLAMA_URL:-http://127.0.0.1:11434/v1}
python_bin="$repo_dir/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  print -u2 "Missing .venv. Run the macOS setup commands from README.md first."
  exit 1
fi
if ! command -v ollama >/dev/null 2>&1; then
  print -u2 "Ollama is not installed or is not on PATH."
  exit 1
fi
if ! ollama list | awk 'NR > 1 {print $1}' | grep -Fxq "$model"; then
  ollama pull "$model"
fi
if ! curl --fail --silent "${endpoint%/v1}/api/tags" >/dev/null; then
  print -u2 "Ollama is not reachable at ${endpoint%/v1}. Start the Ollama app or run: ollama serve"
  exit 1
fi

export PYTHONHASHSEED=${PYTHONHASHSEED:-0}
export HF_HOME=${HF_HOME:-$repo_dir/.cache/huggingface}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-10}
export UTOPIA_DATA_CACHE_DIR=${UTOPIA_DATA_CACHE_DIR:-$repo_dir/.cache/utopia}
mkdir -p "$HF_HOME" "$UTOPIA_DATA_CACHE_DIR" outputs/logs

exec "$python_bin" -B -m utopia \
  --model "$model" \
  --vllm_url "$endpoint" \
  --api-backend ollama \
  --experiment_name exploration_vs_exploitation \
  --experiment_stage smoke \
  --population_mode university_only \
  --num_institutions "${SCIENCEUTOPIA_INSTITUTIONS:-2}" \
  --researchers_per_institution 5 \
  --num_years "${SCIENCEUTOPIA_YEARS:-1}" \
  --num_conferences "${SCIENCEUTOPIA_CONFERENCES:-1}" \
  --seed "${SCIENCEUTOPIA_SEED:-42}" \
  --batch_size "${SCIENCEUTOPIA_BATCH_SIZE:-2}" \
  --rag_device "${SCIENCEUTOPIA_RAG_DEVICE:-cpu}" \
  --log_funding_applications \
  --log_resource_ledger \
  "$@"
