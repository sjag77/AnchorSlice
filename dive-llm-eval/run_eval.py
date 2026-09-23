#!/usr/bin/env python3
"""
Stage 2 - assess DIVE's ground-truth labels against Claude Opus 5.

For each contract in samples.json this shells out to the Claude Code CLI in
headless mode:

    claude -p --output-format json --model opus --tools "" --json-schema ...

Tools are disabled, so the model sees nothing but the Solidity source in the
prompt - no file access, no way to look the answer up. `--json-schema` forces a
parseable label vector back.

Per contract we record wall-clock time, the CLI's own duration_ms/duration_api_ms,
input/output/cache token counts, and cost; those are summed into a totals block.
Agreement with the DIVE labels is then computed per DASP category.

Usage:
    python3 run_eval.py --samples samples.json --out results.json
"""

import argparse
import json
import os
import subprocess
import sys
import time

# running totals recovered from a --resume checkpoint
_RESUMED = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0, "total_tokens": 0,
            "wall": 0.0, "cli_ms": 0, "api_ms": 0, "cost": 0.0}

DASP = [
    "Reentrancy",
    "Access Control",
    "Arithmetic",
    "Unchecked Return Values",
    "DoS",
    "Bad Randomness",
    "Front Running",
    "Time manipulation",
]

SYSTEM_PROMPT_EXAMPLES = """You are a smart contract security auditor. You classify Solidity \
source code against the first 8 categories of the DASP Top 10 taxonomy.

For each category, decide whether the contract contains at least one instance of that \
vulnerability class. A minimal example of each follows - match the shape, not the identifier names.

1. Reentrancy - an external call hands control to the callee before state is settled.
    function withdraw() public {
        uint b = bal[msg.sender];
        (bool ok, ) = msg.sender.call{value: b}("");   // callee regains control here
        bal[msg.sender] = 0;                           // ...and this runs too late
    }
   Also counts: ERC777/ERC721 hooks, tokenFallback, or any callback into untrusted code
   before the caller's own bookkeeping is finished.

2. Access Control - a state-changing or fund-moving path with no authorization gate.
    function setOwner(address o) public { owner = o; }          // anyone becomes owner
    function kill() public { selfdestruct(msg.sender); }        // unprotected selfdestruct
    function withdraw() public { require(tx.origin == owner); } // tx.origin is phishable
   Also counts: an initialize() callable twice, delegatecall to a caller-supplied address,
   a missing modifier on one function of an otherwise-guarded set.

3. Arithmetic - overflow, underflow, or truncation that changes a value.
    // solc < 0.8.0 with no SafeMath:
    function transfer(address to, uint v) public {
        bal[msg.sender] -= v;                 // v > balance underflows to a huge number
        bal[to] += v;
    }
    uint reward = amount * rate / TOTAL;      // multiplication overflows, or / truncates to 0
   Also counts: an unchecked { } block on 0.8+ doing arithmetic on user input.

4. Unchecked Return Values - a low-level call or non-reverting token op whose result is dropped.
    msg.sender.send(amount);                  // returns bool, ignored
    addr.call{value: v}("");                  // returns (bool, bytes), ignored
    token.transfer(to, amount);               // ERC20 that returns false instead of reverting

5. DoS - one participant, or one large input, can block the whole contract.
    for (uint i = 0; i < investors.length; i++)   // unbounded storage array
        investors[i].transfer(amt);               // one reverting payee freezes everyone
   Also counts: a require() inside a loop over user-controlled data, push-payment to an
   address that can reject, or an owner-only unlock that can never be reached.

6. Bad Randomness - a value a miner or validator can see or influence used as a secret.
    uint winner = uint(keccak256(abi.encodePacked(
        block.timestamp, blockhash(block.number - 1), block.difficulty
    ))) % players.length;
   Also counts: block.number, block.coinbase, or a seed committed in a prior transaction.

7. Front Running - the mempool reveals enough to profit by reordering.
    function approve(address s, uint v) public { allowance[msg.sender][s] = v; }
        // the classic ERC20 allowance race: the spender front-runs the change
    function claim(bytes32 answer) public { ... }   // answer is public before it lands
   Also counts: unprotected swaps or auctions with no slippage bound or commit-reveal.

8. Time manipulation - block time or height is a decision variable, not just a record.
    require(block.timestamp >= saleStart);      // a miner can nudge this by seconds
    if (now % 15 == 0) winner = msg.sender;     // timestamp drives the outcome
   Also counts: lock periods, deadlines, or payout schedules gated on block.timestamp /
   block.number where a small shift is worth money.

Rules:
- Judge only the source you are given. Do not assume unseen code.
- A category is 1 if the vulnerability is present, 0 if not. Multiple categories may be 1 for \
the same contract.
- The examples above are minimal on purpose. Real instances are spread across functions, hidden \
behind modifiers and inheritance, or reachable only through a helper - match the underlying shape, \
not the surface syntax.
- Be a working auditor, not a linter: report the flaw only when it is actually reachable and \
exploitable, not when a pattern merely appears.
- Give a confidence in [0,1] per category and one short reason per category you mark 1.
- Reply with the JSON object only."""


SYSTEM_PROMPT_BRIEF = """You are a smart contract security auditor. You classify Solidity \
source code against the first 8 categories of the DASP Top 10 taxonomy.

For each category, decide whether the contract contains at least one instance of \
that vulnerability class:

1. Reentrancy - external call before state update, unguarded callback re-entry.
2. Access Control - missing/incorrect authorization on privileged functions, \
unprotected selfdestruct or delegatecall, tx.origin auth, uninitialized owner.
3. Arithmetic - integer overflow/underflow (pre-0.8.0 without SafeMath, or inside \
an `unchecked` block), precision-loss truncation used in value calculations.
4. Unchecked Return Values - return value of call/send/delegatecall/callcode or a \
non-reverting ERC20 transfer is ignored.
5. DoS - unbounded loop over storage, a revert in a loop blocking all participants, \
push-payment to an address that can reject, gas-limit griefing.
6. Bad Randomness - randomness derived from block.timestamp, blockhash, block.number, \
block.difficulty/prevrandao, or other miner/validator-influenceable values.
7. Front Running - outcome depends on transaction ordering in a way an observer can \
profit from (approve race, unprotected swaps/auctions, commit-less reveal).
8. Time manipulation - logic depends on block.timestamp / block.number in a way a \
miner can nudge for advantage.

Rules:
- Judge only the source you are given. Do not assume unseen code.
- A category is 1 if the vulnerability is present, 0 if not. Multiple categories \
may be 1 for the same contract.
- Be a working auditor, not a linter: report the flaw only when it is actually \
reachable and exploitable, not when a pattern merely appears.
- Give a confidence in [0,1] per category and one short reason per category you \
mark 1.
- Reply with the JSON object only."""


SYSTEM_PROMPT_CALIBRATED = SYSTEM_PROMPT_EXAMPLES.replace(
    """Rules:
- Judge only the source you are given. Do not assume unseen code.""",
    """How to set your threshold:

You are being compared against a consensus of six static analyzers (MAIAN, Mythril, \
Semgrep, Slither, Solhint, VeriSmart) mapped onto these categories. Match that decision \
boundary. A detector fires when the vulnerable *pattern* is present and nothing in the \
code visibly neutralises it - it does not require you to write the exploit first. Mark 1 \
when the pattern is present and not demonstrably mitigated; mark 0 only when the code \
actively prevents it (a guard, a reentrancy lock, SafeMath, a bounded loop) or the \
construct is simply absent.

Concretely, these all warrant a 1:
- Reentrancy: any call into a non-trusted address - .call/.send/.transfer with a value, a \
token hook, a callback - with ANY state write or event emission after it. Event-after-call \
counts. So does a call inside a loop.
- Access Control: any external or public state-changing function reachable with no modifier \
and no require on the caller. Also owner setters with no zero-address check, and any \
selfdestruct, delegatecall, or upgrade path.
- Arithmetic: on solc < 0.8.0, any +, -, or * on a value a caller influences, unless every \
such operation routes through SafeMath. On 0.8+, any unchecked block. Division before \
multiplication counts as truncation.
- Unchecked Return Values: any .call / .send / .delegatecall whose bool is not read, and any \
ERC20 .transfer/.transferFrom whose return value is ignored.
- DoS: any loop whose bound is a dynamic array, mapping length, or caller-supplied number - \
especially one containing a transfer, an external call, or a require.
- Bad Randomness: any use of block.timestamp, now, blockhash, block.number, block.difficulty, \
block.prevrandao or block.coinbase to select, order, or reward.
- Front Running: any ERC20-style approve that sets an allowance directly, and any public \
function whose payoff depends on landing before someone else - claims, swaps, auctions, \
first-come rewards.
- Time manipulation: any comparison or branch on block.timestamp, now, or block.number.

Calibration: contracts in this corpus carry 2.4 categories on average, and many carry four \
or more. If you have marked fewer than two, walk the eight categories again before answering \
- a missed pattern is the more common error, not an over-call.

Rules:
- Judge only the source you are given. Do not assume unseen code.
- Consider all eight categories in order. Do not skip one because the contract "looks clean".""",
).replace(
    """- Be a working auditor, not a linter: report the flaw only when it is actually reachable and \
exploitable, not when a pattern merely appears.
""",
    "",
)


SYSTEM_PROMPT_CALIBRATED2 = SYSTEM_PROMPT_CALIBRATED.replace(
    "- Unchecked Return Values: any .call / .send / .delegatecall whose bool is not read, and any \
ERC20 .transfer/.transferFrom whose return value is ignored.",
    "- Unchecked Return Values: a .call / .send / .delegatecall whose bool is discarded, or an ERC20 \
.transfer/.transferFrom whose return value is ignored. If the result is consumed by require, assert, an \
if, or an assignment, it is checked: mark 0.",
).replace(
    "- DoS: any loop whose bound is a dynamic array, mapping length, or caller-supplied number - \
especially one containing a transfer, an external call, or a require.",
    "- DoS: a loop whose bound is a dynamic array, mapping length, or caller-supplied number, especially \
one containing a transfer or external call; or a push-payment that a payee can make revert. A require, \
revert or assert on its own is ordinary input validation, not DoS.",
).replace(
    "- Front Running: any ERC20-style approve that sets an allowance directly, and any public function \
whose payoff depends on landing before someone else - claims, swaps, auctions, first-come rewards.",
    "- Front Running: the ERC20 approve allowance race, or a function whose payoff demonstrably depends \
on landing before someone else - auctions, first-come rewards, swaps without a slippage bound. A payable \
function, a stored price, or ordinary state updates are not front running by themselves.",
).replace(
    "- Time manipulation: any comparison or branch on block.timestamp, now, or block.number.",
    "- Time manipulation: a comparison or branch on block.timestamp, now, or block.number that decides a \
payout, an eligibility window, or a winner. Recording or emitting a timestamp is not enough.",
).replace(
    "Calibration: contracts in this corpus carry 2.4 categories on average",
    "Base rates in this corpus: Access Control 75%, Reentrancy 51%, Arithmetic 43%, Time manipulation 28%, \
Unchecked Return Values 27%, DoS 17%, Bad Randomness 3%, Front Running 3%. The last two are rare: mark them \
only on specific evidence.\n\nCalibration: contracts in this corpus carry 2.4 categories on average",
)

SYSTEM_PROMPT_CALIBRATED3 = SYSTEM_PROMPT_CALIBRATED2.replace(
    "- Bad Randomness: any use of block.timestamp, now, blockhash, block.number, block.difficulty, \
block.prevrandao or block.coinbase to select, order, or reward.",
    "- Bad Randomness: this corpus marks it whenever block.number, blockhash, block.difficulty, \
block.prevrandao or block.coinbase influences a decision or a stored value, even when nothing random is \
intended - a sale window gated on block.number counts. block.timestamp on its own usually does not.",
).replace(
    "- Time manipulation: a comparison or branch on block.timestamp, now, or block.number that decides a \
payout, an eligibility window, or a winner. Recording or emitting a timestamp is not enough.",
    "- Time manipulation: block.timestamp or now deciding a payout, lock, deadline or eligibility window. \
Recording or emitting a timestamp is not enough, and a contract that only uses block.number belongs to Bad \
Randomness rather than here.",
).replace(
    "- Unchecked Return Values: a .call / .send / .delegatecall whose bool is discarded, or an ERC20 \
.transfer/.transferFrom whose return value is ignored. If the result is consumed by require, assert, an \
if, or an assignment, it is checked: mark 0.",
    "- Unchecked Return Values: a low-level .call / .send / .delegatecall / .callcode whose bool is \
discarded, or an ERC20 .transfer/.transferFrom whose returned bool is ignored. A result consumed by \
require, assert, an if, or an assignment is checked: mark 0. An ignored approve() to a router or pair, and \
a payable address .transfer() that reverts on failure, do not count.",
).replace(
    "- DoS: a loop whose bound is a dynamic array, mapping length, or caller-supplied number, especially \
one containing a transfer or external call; or a push-payment that a payee can make revert. A require, \
revert or assert on its own is ordinary input validation, not DoS.",
    "- DoS: a loop over a storage array or mapping that untrusted callers can grow without bound, \
especially one containing a transfer or external call; or a payment whose failure blocks other users. A \
loop over an argument the caller passes in, an owner-only batch, a fixed bound, or a bare require is not \
DoS.",
)

SYSTEM_PROMPT_CALIBRATED4 = SYSTEM_PROMPT_CALIBRATED3.replace(
    "- Unchecked Return Values: a low-level .call / .send / .delegatecall / .callcode whose bool is \
discarded, or an ERC20 .transfer/.transferFrom whose returned bool is ignored. A result consumed by \
require, assert, an if, or an assignment is checked: mark 0. An ignored approve() to a router or pair, and \
a payable address .transfer() that reverts on failure, do not count.",
    "- Unchecked Return Values: in this corpus the label tracks the presence of a raw low-level call. Mark \
1 when the contract contains .call(, .call{, .call., .callcode or .delegatecall anywhere, including inside \
a helper library, whether or not the returned bool is checked. A contract whose only external calls are \
.send(), .transfer(), approve() or ERC20 transfer/transferFrom is normally 0.",
).replace(
    "- DoS: a loop over a storage array or mapping that untrusted callers can grow without bound, \
especially one containing a transfer or external call; or a payment whose failure blocks other users. A \
loop over an argument the caller passes in, an owner-only batch, a fixed bound, or a bare require is not \
DoS.",
    "- DoS: mark 1 for any of three shapes - a while loop; a for/while loop whose body performs a \
.send/.transfer/.call; or a push payment guarded by if (!addr.send(...)) or assert(addr.send(...)), where \
one failing payee blocks the flow. A plain for loop over a caller-supplied argument, an owner-only batch, \
a fixed bound, or a bare require is 0.",
)

SYSTEM_PROMPT_CALIBRATED5 = SYSTEM_PROMPT_CALIBRATED4.replace(
    "- Bad Randomness: this corpus marks it whenever block.number, blockhash, block.difficulty, \
block.prevrandao or block.coinbase influences a decision or a stored value, even when nothing random is \
intended - a sale window gated on block.number counts. block.timestamp on its own usually does not.",
    "- Bad Randomness: mark 1 when blockhash, block.difficulty, block.prevrandao or block.coinbase is \
used at all, when block.number takes part in arithmetic that derives a value or an index, or when a hash \
(keccak256/sha3) is computed over a block value or timestamp. A plain comparison against block.number, such \
as a sale window or a lock period, is usually not marked in this corpus: mark 0 unless one of the shapes \
above is present.",
)

PROMPTS = {
    "brief": SYSTEM_PROMPT_BRIEF,
    "examples": SYSTEM_PROMPT_EXAMPLES,
    "calibrated": SYSTEM_PROMPT_CALIBRATED,
    "calibrated2": SYSTEM_PROMPT_CALIBRATED2,
    "calibrated3": SYSTEM_PROMPT_CALIBRATED3,
    "calibrated4": SYSTEM_PROMPT_CALIBRATED4,
    "calibrated5": SYSTEM_PROMPT_CALIBRATED5,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "object",
            "properties": {c: {"type": "integer", "enum": [0, 1]} for c in DASP},
            "required": DASP,
            "additionalProperties": False,
        },
        "confidence": {
            "type": "object",
            "properties": {c: {"type": "number"} for c in DASP},
            "required": DASP,
            "additionalProperties": False,
        },
        "reasons": {
            "type": "object",
            "description": "category -> one-sentence justification, only for categories marked 1",
            "additionalProperties": {"type": "string"},
        },
    },
    "required": ["labels", "confidence", "reasons"],
    "additionalProperties": False,
}


SLICE_PREAMBLE = """This contract has been reduced by a STATIC pre-filter before \
being shown to you. Lines that matched no lexical anchor for any DASP category were \
removed, standard unmodified library code (SafeMath, IERC20, Ownable, ...) was collapsed \
to a stub, and the remainder is grouped into numbered blocks.

Each block header lists the categories whose anchors fired inside it, e.g.
    // --- BLOCK 4 | src L37-60 | candidates: Reentrancy, Arithmetic

Read those tags as PURELY LEXICAL hints, not findings. The filter has no understanding of \
the code; a tag only means some token associated with that category appears in the block. \
Most tagged blocks are not vulnerable. Judge each block on its merits and mark a category 1 \
only when the flaw is genuinely present and reachable.

The filter is tuned for recall: on the validation set every labelled vulnerability survived \
it. So if a category is tagged nowhere in the contract, it is very likely absent - but you \
may still mark it 1 if the code you can see clearly shows it.

Omitted code contained no anchor for any category. Do not speculate about it."""


def build_prompt(sample, sliced=False):
    note = ("\n\n[NOTE: source truncated to the first %d characters of %d]"
            % (len(sample["source"]), sample["source_chars"])) if sample["truncated"] else ""
    if sliced:
        return (
            "Classify the following Solidity contract against DASP categories 1-8.\n\n"
            + SLICE_PREAMBLE + "\n\n```solidity\n" + sample["source"] + "\n```" + note
        )
    return (
        "Classify the following Solidity contract against DASP categories 1-8.\n\n"
        "```solidity\n" + sample["source"] + "\n```" + note
    )


def call_claude(prompt, model, effort, timeout, system):
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", model,
        "--effort", effort,
        "--tools", "",                       # no tool access - pure source-code judgment
        "--system-prompt", system,
        "--json-schema", json.dumps(SCHEMA),
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        return None, wall, proc.stderr.strip()[:2000]
    try:
        return json.loads(proc.stdout), wall, None
    except json.JSONDecodeError as e:
        return None, wall, f"unparseable CLI output: {e}\n{proc.stdout[:1000]}"


def extract_prediction(envelope):
    """With --json-schema the CLI returns the validated object in `structured_output`;
    fall back to parsing `result` if that field is absent."""
    so = envelope.get("structured_output")
    if isinstance(so, dict) and "labels" in so:
        return so
    res = envelope.get("result")
    if isinstance(res, dict):
        return res
    if isinstance(res, str):
        s = res.strip()
        if s.startswith("```"):
            s = s.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(s)
    raise ValueError(f"no usable result field: {list(envelope)}")


def usage_of(envelope):
    u = envelope.get("usage") or {}
    inp = u.get("input_tokens", 0)
    out = u.get("output_tokens", 0)
    cc = u.get("cache_creation_input_tokens", 0)
    cr = u.get("cache_read_input_tokens", 0)
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_creation_input_tokens": cc,
        "cache_read_input_tokens": cr,
        "total_tokens": inp + out + cc + cr,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default="samples.json")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--model", default="opus", help="CLI model alias or full id")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--prompt", default="calibrated", choices=["brief", "examples", "calibrated", "calibrated2", "calibrated3", "calibrated4", "calibrated5"],
                    help="'brief' = one-line category definitions; "
                         "'examples' = each definition carries a minimal code example")
    ap.add_argument("--slicer", default="slice", help="slicer module to use with --slice")
    ap.add_argument("--slice", action="store_true",
                    help="run slice.py's static pre-filter over each contract's source "
                         "before prompting, and tell the model how to read the blocks")
    ap.add_argument("--resume", action="store_true",
                    help="skip contracts already present in --out and keep their results; "
                         "partial results are checkpointed after every contract, so an "
                         "interrupted run can be continued rather than repeated")
    args = ap.parse_args()

    data = json.load(open(args.samples))
    samples = data["samples"]

    if args.slice:
        slicer = __import__(args.slicer)
        pre = post = 0
        for smp in samples:
            pre += len(smp["source"])
            smp["sliced_source"] = slicer.render(smp["source"], smp["contractID"])
            smp["source"] = smp["sliced_source"]
            post += len(smp["source"])
        print("pre-slice: %d -> %d chars (%.1f%%) across %d contracts\n"
              % (pre, post, 100.0 * post / pre, len(samples)))

    ckpt = args.out + ".partial"
    records = []
    if args.resume:
        for path in (ckpt, args.out):
            if os.path.exists(path):
                records = json.load(open(path)).get("records", [])
                print(f"resuming from {path}: {len(records)} contracts already done")
                break
        # only completed contracts count as done - errored ones get retried
        records = [r for r in records if "prediction" in r]
        done = {r["contractID"] for r in records}
        samples = [s for s in samples if s["contractID"] not in done]
        if not samples:
            print("nothing left to do")
        # restore running totals from the recovered records
        for r in records:
            u = r.get("usage") or {}
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                      "cache_read_input_tokens", "total_tokens"):
                _RESUMED[k] += u.get(k, 0)
            _RESUMED["wall"] += r.get("wall_seconds", 0)
            _RESUMED["cli_ms"] += r.get("cli_duration_ms", 0)
            _RESUMED["api_ms"] += r.get("api_duration_ms", 0)
            _RESUMED["cost"] += r.get("cost_usd", 0.0)
    totals = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
              "cache_read_input_tokens": 0, "total_tokens": 0}
    total_wall = 0.0
    total_cli_ms = 0
    total_api_ms = 0
    total_cost = 0.0

    def flush():
        """Write partial results after every contract so an interrupt loses at most one call."""
        json.dump({"records": records}, open(ckpt, "w"))

    run_t0 = time.perf_counter()
    for i, s in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] contract {s['contractID']} "
              f"({s['source_chars']} chars) ...", end="", flush=True)
        envelope, wall, err = call_claude(build_prompt(s, args.slice), args.model, args.effort,
                                          args.timeout, PROMPTS[args.prompt])
        total_wall += wall

        if err:
            print(f" FAILED after {wall:.1f}s")
            records.append({"contractID": s["contractID"], "error": err,
                            "wall_seconds": round(wall, 2)})
            flush()
            continue

        usage = usage_of(envelope)
        for k in totals:
            totals[k] += usage[k]
        cli_ms = envelope.get("duration_ms", 0)
        api_ms = envelope.get("duration_api_ms", 0)
        cost = envelope.get("total_cost_usd", 0.0) or 0.0
        total_cli_ms += cli_ms
        total_api_ms += api_ms
        total_cost += cost

        try:
            pred = extract_prediction(envelope)
        except Exception as e:  # noqa: BLE001 - record and continue the run
            print(f" UNPARSEABLE ({e})")
            records.append({"contractID": s["contractID"], "error": str(e),
                            "wall_seconds": round(wall, 2), "usage": usage})
            flush()
            continue

        gt = s["ground_truth"]
        pl = pred["labels"]
        agree = sum(1 for c in DASP if pl[c] == gt[c])
        print(f" {wall:6.1f}s  {usage['total_tokens']:>7} tok  agree {agree}/8")

        records.append({
            "contractID": s["contractID"],
            "source_chars": s["source_chars"],
            "truncated": s["truncated"],
            "ground_truth": gt,
            "prediction": pl,
            "confidence": pred.get("confidence", {}),
            "reasons": pred.get("reasons", {}),
            "agreement": agree,
            "wall_seconds": round(wall, 2),
            "cli_duration_ms": cli_ms,
            "api_duration_ms": api_ms,
            "usage": usage,
            "cost_usd": cost,
            "num_turns": envelope.get("num_turns"),
            "session_id": envelope.get("session_id"),
        })

        flush()

    run_wall = time.perf_counter() - run_t0

    # ---- agreement metrics, per DASP category ----
    scored = [r for r in records if "prediction" in r and "ground_truth" in r]
    per_cat = {}
    for c in DASP:
        tp = sum(1 for r in scored if r["ground_truth"][c] == 1 and r["prediction"][c] == 1)
        tn = sum(1 for r in scored if r["ground_truth"][c] == 0 and r["prediction"][c] == 0)
        fp = sum(1 for r in scored if r["ground_truth"][c] == 0 and r["prediction"][c] == 1)
        fn = sum(1 for r in scored if r["ground_truth"][c] == 1 and r["prediction"][c] == 0)
        n = tp + tn + fp + fn
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else (0.0 if tp + fp + fn else None)
        # Cohen's kappa - chance-corrected agreement between DIVE and the LLM
        po = (tp + tn) / n if n else None
        pe = (((tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)) / (n * n)) if n else None
        kappa = ((po - pe) / (1 - pe)) if (po is not None and pe is not None and pe != 1) else None
        per_cat[c] = {"tp": tp, "tn": tn, "fp": fp, "fn": fn,
                      "dive_positives": tp + fn, "llm_positives": tp + fp,
                      "agreement": round(po, 4) if po is not None else None,
                      "precision_vs_dive": round(prec, 4) if prec is not None else None,
                      "recall_vs_dive": round(rec, 4) if rec is not None else None,
                      "f1_vs_dive": round(f1, 4) if f1 is not None else None,
                      "cohens_kappa": round(kappa, 4) if kappa is not None else None}

    total_cells = len(scored) * len(DASP)
    summary = {
        "model": args.model,
        "effort": args.effort,
        "prompt_variant": args.prompt,
        "sliced": bool(args.slice),
        "contracts_evaluated": len(scored),
        "contracts_failed": len(records) - len(scored),
        "exact_match_all_8": sum(1 for r in scored if r["agreement"] == 8),
        "label_agreement": round(sum(r["agreement"] for r in scored) / total_cells, 4) if total_cells else None,
        "hamming_loss": round(1 - sum(r["agreement"] for r in scored) / total_cells, 4) if total_cells else None,
        "per_category": per_cat,
        "timing": {
            "run_wall_seconds": round(run_wall, 2),
            "sum_per_call_wall_seconds": round(total_wall, 2),
            "sum_cli_duration_ms": total_cli_ms,
            "sum_api_duration_ms": total_api_ms,
            "mean_wall_seconds_per_contract": round(total_wall / len(records), 2) if records else None,
        },
        "tokens": totals,
        "cost_usd": round(total_cost, 4),
    }

    json.dump({"summary": summary, "records": records}, open(args.out, "w"), indent=2)
    if os.path.exists(ckpt):
        os.remove(ckpt)

    print("\n" + "=" * 74)
    print(f"Model {args.model} (effort={args.effort}, prompt={args.prompt}) vs DIVE labels "
          f"- {summary['contracts_evaluated']} contracts")
    print("=" * 74)
    print(f"Label agreement    : {summary['label_agreement']}  "
          f"({sum(r['agreement'] for r in scored)}/{total_cells} label cells)")
    print(f"Exact match (8/8)  : {summary['exact_match_all_8']}/{summary['contracts_evaluated']}")
    print(f"Hamming loss       : {summary['hamming_loss']}")
    print()
    print(f"{'category':<24}{'DIVE+':>6}{'LLM+':>6}{'TP':>4}{'FP':>4}{'FN':>4}"
          f"{'agree':>8}{'kappa':>8}")
    for c in DASP:
        m = per_cat[c]
        k = f"{m['cohens_kappa']:.3f}" if m["cohens_kappa"] is not None else "  n/a"
        print(f"{c:<24}{m['dive_positives']:>6}{m['llm_positives']:>6}{m['tp']:>4}"
              f"{m['fp']:>4}{m['fn']:>4}{m['agreement']:>8.3f}{k:>8}")
    print()
    t = summary["timing"]
    print(f"Wall clock         : {t['run_wall_seconds']}s total, "
          f"{t['mean_wall_seconds_per_contract']}s/contract")
    print(f"API time (CLI)     : {t['sum_api_duration_ms']/1000:.1f}s")
    print(f"Tokens             : {totals['total_tokens']} total "
          f"(in {totals['input_tokens']}, out {totals['output_tokens']}, "
          f"cache-write {totals['cache_creation_input_tokens']}, "
          f"cache-read {totals['cache_read_input_tokens']})")
    print(f"Cost               : ${summary['cost_usd']}")
    print(f"\nFull results -> {args.out}")


if __name__ == "__main__":
    main()
