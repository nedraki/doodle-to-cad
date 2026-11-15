#!/usr/bin/env bash
# run_jailed.sh — run a heavy batch command inside its own memory-capped
# systemd scope so a runaway process dies in ITS cgroup, never globally.
#
# Why: this box (DGX Spark, GB10) shares one memory pool between CPU and the
# vLLM engine (~91 GiB resident). A runaway python that grows past the
# remaining ~30 GiB triggers a GLOBAL OOM and takes the inference engine with
# it (5 confirmed kernel kills, Nov 1-3 2026, all from uncapped snap3d runs).
# The jail turns that failure into rc=137 inside this scope, engine intact.
#
# usage: scripts/run_jailed.sh [-m MEMMAX] [-t SECS] [-o PEAKLOG] -- <cmd...>
#   -m  MemoryMax for the scope (default 16G; keep well under free -h avail)
#   -t  RuntimeMaxSec, hard wall-clock cap (default 3600)
#   -o  append one JSON peak-RSS line to this file (default: stderr only)
#
# Swap is disabled inside the jail (MemorySwapMax=0): spilling a runaway to
# swap survives the cap but thrashes the shared pool — same engine death,
# slower. A jailed run must either fit in RAM or die as rc=137.
#
# Policy (OOM-INCIDENT-2026-11-03): every agent-launched heavy run
# (trimesh/mujoco/booleans on arbitrary meshes, batch sweeps) goes through
# this wrapper. Wrap the DRIVER, not the leaf script — batch drivers spawn
# the children and inherit the scope. NEVER retry a run that died with empty
# output / signal 9 without reading the kernel OOM lines this script prints.
set -u

mem=16G; tmo=3600; peaklog=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) mem="${2:-}"; shift 2 ;;
    -t) tmo="${2:-}"; shift 2 ;;
    -o) peaklog="${2:-}"; shift 2 ;;
    --) shift; break ;;
    *) echo "usage: $0 [-m MEM] [-t SECS] [-o LOG] -- cmd..." >&2; exit 2 ;;
  esac
done
if [[ $# -eq 0 ]]; then echo "run_jailed: no command given" >&2; exit 2; fi

# Fail CLOSED: if the jail cannot be created, refuse to run unjailed.
if ! command -v systemd-run >/dev/null || \
   ! systemd-run --user --scope -p MemoryMax=32M -p MemorySwapMax=0 -- /bin/true >/dev/null 2>&1; then
  echo "run_jailed: cannot create a user systemd scope — refusing to run unjailed" >&2
  exit 3
fi

err=$(mktemp); trap 'rm -f "$err"' EXIT
systemd-run --user --scope -p MemoryMax="$mem" -p MemorySwapMax=0 \
  -p RuntimeMaxSec="$tmo" -p TimeoutStopSec=10 -- "$@" 2>"$err" &
pid=$!

# Resolve the scope's cgroup path (systemd-run prints the unit name; the
# command's own stderr is untouched — it inherits our terminal).
unit=""; cg=""
for _ in $(seq 1 25); do
  unit=$(grep -oE 'run-[a-z0-9.]+\.scope' "$err" 2>/dev/null | head -1)
  if [[ -n "$unit" ]]; then
    cg=$(systemctl --user show "$unit" -p ControlGroup --value 2>/dev/null || true)
    [[ "$cg" == /* ]] && break
  fi
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.2
done
[[ "$cg" == /* ]] || cg=""

# Peak-RSS sampler while the jail lives.
peak=0
while kill -0 "$pid" 2>/dev/null; do
  cur=0
  if [[ -n "$cg" && -r "/sys/fs/cgroup$cg/memory.current" ]]; then
    cur=$(cat "/sys/fs/cgroup$cg/memory.current" 2>/dev/null || echo 0)
  fi
  [[ "$cur" =~ ^[0-9]+$ ]] && (( cur > peak )) && peak=$cur
  sleep 1
done
set +e; wait "$pid"; rc=$?; set -e

# Prefer the kernel-recorded peak (systemd >= 254), queryable post-mortem.
if [[ -n "$unit" ]]; then
  for _ in 1 2 3; do
    pk=$(systemctl --user show "$unit" -p MemoryPeak --value 2>/dev/null || echo 0)
    if [[ "$pk" =~ ^[0-9]+$ ]]; then
      (( pk > peak )) && peak=$pk
      (( pk > 0 )) && break
    else
      break
    fi
    sleep 0.3
  done
fi
peak_mib=$(( peak / 1048576 ))
echo "run_jailed: peak RSS ${peak_mib} MiB (cap ${mem})" >&2
if [[ -n "$peaklog" ]]; then
  printf '{"ts":"%s","peak_rss_mib":%s,"cap":"%s","rc":%s,"cmd":"%s"}\n' \
    "$(date -Is)" "$peak_mib" "$mem" "$rc" "$*" >> "$peaklog"
fi

# OOM-first triage (incident rule §4.5): a signal-death is suspect until the
# kernel log says otherwise. A "Memory cgroup out of memory" line means the
# jail did its job; a "global_oom" line means something escaped — escalate.
if [[ $rc -ge 128 ]]; then
  echo "run_jailed: command died on signal $(( rc - 128 )) — last kernel OOM lines:" >&2
  journalctl -k --since "-10 min" --no-pager 2>/dev/null \
    | grep -iE "oom|killed process" | tail -6 >&2 || true
  if [[ $rc -eq 137 ]]; then
    echo "run_jailed: verdict -> jailed OOM or timeout (MemoryMax=${mem}, RuntimeMaxSec=${tmo})." >&2
    echo "run_jailed: DO NOT blind-retry. Shrink the input case first, check peak RSS." >&2
  fi
fi
exit $rc
