# Exact payload sent for each contract

```
claude -p --output-format json --model opus --effort high \
  --tools "" --system-prompt <SYSTEM> --json-schema <SCHEMA> \
  --disable-slash-commands --strict-mcp-config --no-session-persistence
```

`--tools ""` removes all tool access: the model sees only the text below.

## 1. System prompt — CURRENT (`--prompt examples`)

Each category carries a minimal worked example.

```
You are a smart contract security auditor. You classify Solidity source code against the first 8 categories of the DASP Top 10 taxonomy.

For each category, decide whether the contract contains at least one instance of that vulnerability class. A minimal example of each follows - match the shape, not the identifier names.

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
- A category is 1 if the vulnerability is present, 0 if not. Multiple categories may be 1 for the same contract.
- The examples above are minimal on purpose. Real instances are spread across functions, hidden behind modifiers and inheritance, or reachable only through a helper - match the underlying shape, not the surface syntax.
- Be a working auditor, not a linter: report the flaw only when it is actually reachable and exploitable, not when a pattern merely appears.
- Give a confidence in [0,1] per category and one short reason per category you mark 1.
- Reply with the JSON object only.
```

## 2. System prompt — SUPERSEDED (`--prompt brief`)

One-line definitions, kept for the A/B comparison.

```
You are a smart contract security auditor. You classify Solidity source code against the first 8 categories of the DASP Top 10 taxonomy.

For each category, decide whether the contract contains at least one instance of that vulnerability class:

1. Reentrancy - external call before state update, unguarded callback re-entry.
2. Access Control - missing/incorrect authorization on privileged functions, unprotected selfdestruct or delegatecall, tx.origin auth, uninitialized owner.
3. Arithmetic - integer overflow/underflow (pre-0.8.0 without SafeMath, or inside an `unchecked` block), precision-loss truncation used in value calculations.
4. Unchecked Return Values - return value of call/send/delegatecall/callcode or a non-reverting ERC20 transfer is ignored.
5. DoS - unbounded loop over storage, a revert in a loop blocking all participants, push-payment to an address that can reject, gas-limit griefing.
6. Bad Randomness - randomness derived from block.timestamp, blockhash, block.number, block.difficulty/prevrandao, or other miner/validator-influenceable values.
7. Front Running - outcome depends on transaction ordering in a way an observer can profit from (approve race, unprotected swaps/auctions, commit-less reveal).
8. Time manipulation - logic depends on block.timestamp / block.number in a way a miner can nudge for advantage.

Rules:
- Judge only the source you are given. Do not assume unseen code.
- A category is 1 if the vulnerability is present, 0 if not. Multiple categories may be 1 for the same contract.
- Be a working auditor, not a linter: report the flaw only when it is actually reachable and exploitable, not when a pattern merely appears.
- Give a confidence in [0,1] per category and one short reason per category you mark 1.
- Reply with the JSON object only.
```

## 3. User message (stdin) — shown for contract 10268

```
Classify the following Solidity contract against DASP categories 1-8.

```solidity
// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;


interface IBoooooost {
    function cloneContract(address implementation) external returns (address);
    function initialize(
        address _stakedToken,
        address _rewardToken,
        uint256 _duration,
        address _manager,
        address _treasury
    ) external;
    function setTreasuryFee(uint256 _fee) external;
    function transferOwnership(address owner) external;
}

contract BeefyBoostFactory {
    address public factory;
    address public boostImpl;
    address public deployer;

    event BoostDeployed(address indexed boost);

    constructor(address _factory, address _boostImpl) {
        factory = _factory;
        boostImpl = _boostImpl;
        deployer = msg.sender;
    }

    function booooost(address mooToken, address rewardToken, uint duration_in_sec) external {
        IBoooooost boost = IBoooooost(IBoooooost(factory).cloneContract(boostImpl));
        boost.initialize(mooToken, rewardToken, duration_in_sec, msg.sender, address(0));
        boost.setTreasuryFee(0);
        boost.transferOwnership(deployer);
        emit BoostDeployed(address(boost));
    }
}
```
```

## 4. JSON schema forcing the reply shape

```json
{
  "type": "object",
  "properties": {
    "labels": {
      "type": "object",
      "properties": {
        "Reentrancy": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Access Control": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Arithmetic": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Unchecked Return Values": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "DoS": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Bad Randomness": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Front Running": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "Time manipulation": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        }
      },
      "required": [
        "Reentrancy",
        "Access Control",
        "Arithmetic",
        "Unchecked Return Values",
        "DoS",
        "Bad Randomness",
        "Front Running",
        "Time manipulation"
      ],
      "additionalProperties": false
    },
    "confidence": {
      "type": "object",
      "properties": {
        "Reentrancy": {
          "type": "number"
        },
        "Access Control": {
          "type": "number"
        },
        "Arithmetic": {
          "type": "number"
        },
        "Unchecked Return Values": {
          "type": "number"
        },
        "DoS": {
          "type": "number"
        },
        "Bad Randomness": {
          "type": "number"
        },
        "Front Running": {
          "type": "number"
        },
        "Time manipulation": {
          "type": "number"
        }
      },
      "required": [
        "Reentrancy",
        "Access Control",
        "Arithmetic",
        "Unchecked Return Values",
        "DoS",
        "Bad Randomness",
        "Front Running",
        "Time manipulation"
      ],
      "additionalProperties": false
    },
    "reasons": {
      "type": "object",
      "description": "category -> one-sentence justification, only for categories marked 1",
      "additionalProperties": {
        "type": "string"
      }
    }
  },
  "required": [
    "labels",
    "confidence",
    "reasons"
  ],
  "additionalProperties": false
}
```
