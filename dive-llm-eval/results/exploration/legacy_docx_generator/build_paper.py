#!/usr/bin/env python3
"""Build the IEEE-format manuscript as RTF (converted to .doc by textutil)."""
import os, struct, binascii

HERE = os.path.dirname(os.path.abspath(__file__))

ITEMS = []

def esc(t):
    out = []
    for ch in t:
        if ch == '\\': out.append('\\\\')
        elif ch == '{': out.append('\\{')
        elif ch == '}': out.append('\\}')
        elif ord(ch) < 128: out.append(ch)
        else: out.append('\\u%d?' % ord(ch))
    return ''.join(out)

# ---------------------------------------------------------------- paragraphs
def P(t, sz=20, just='\\qj', first=True, sb=0, sa=0, extra=''):
    ITEMS.append(('p', t, first, sz))
    ind = '\\fi200' if first else '\\fi0'
    return ('\\pard%s%s\\sb%d\\sa%d\\li0\\ri0%s\\f0\\fs%d %s\\par\n'
            % (just, ind, sb, sa, extra, sz, esc(t)))

def H1(n, t):
    ITEMS.append(('h1', n, t))
    return ('\\pard\\keepn\\qc\\fi0\\sb160\\sa80\\f0\\fs20\\scaps %s.  %s\\par\n'
            % (esc(n), esc(t)))

def H2(t):
    ITEMS.append(('h2', t))
    return ('\\pard\\keepn\\ql\\fi0\\sb100\\sa60\\f0\\fs20\\i %s\\par\n' % esc(t))

def H5(t):
    ITEMS.append(('h5', t))
    return ('\\pard\\keepn\\qc\\fi0\\sb160\\sa80\\f0\\fs20\\scaps %s\\par\n' % esc(t))

# ---------------------------------------------------------------- tables
def table(rows, widths, head_rows=1, fs=16):
    """rows: list of list[str]; widths: cumulative twips"""
    ITEMS.append(('table', rows, head_rows, widths))
    out = []
    for ri, row in enumerate(rows):
        top = '\\clbrdrt\\brdrs\\brdrw10' if ri == 0 else ''
        bot = '\\clbrdrb\\brdrs\\brdrw10' if (ri == head_rows - 1 or ri == len(rows) - 1) else ''
        out.append('\\trowd\\trgaph40\\trleft0\\trrh0')
        for w in widths:
            out.append('%s%s\\clvertalc\\cellx%d' % (top, bot, w))
        out.append('\n')
        for ci, cell in enumerate(row):
            al = '\\ql' if ci == 0 else '\\qr'
            style = '\\b' if ri < head_rows else ''
            out.append('\\pard\\intbl\\fi0\\sb20\\sa20%s\\f0\\fs%d%s %s\\cell '
                       % (al, fs, style, esc(cell)))
        out.append('\\row\n')
    return ''.join(out)

def wide_start():
    ITEMS.append(('wide_start',))
    return '\\sect\\sectd\\sbknone\\cols1\\linex0\n'

def wide_end():
    ITEMS.append(('wide_end',))
    return '\\sect\\sectd\\sbknone\\cols2\\colsx397\\linex0\n'

def caption(t, sz=16):
    ITEMS.append(('cap', t))
    return '\\pard\\qc\\fi0\\sb60\\sa100\\f0\\fs%d %s\\par\n' % (sz, esc(t))

def tblhead(t, sz=16):
    ITEMS.append(('tblhead', t))
    return '\\pard\\keepn\\qc\\fi0\\sb140\\sa60\\f0\\fs%d\\scaps %s\\par\n' % (sz, esc(t))

# ---------------------------------------------------------------- images
def picture(path, goal_w):
    ITEMS.append(('img', path, goal_w))
    d = open(path, 'rb').read()
    w, h = struct.unpack('>II', d[16:24])
    gh = int(goal_w * h / w)
    hexd = binascii.hexlify(d).decode()
    lines = '\n'.join(hexd[i:i+128] for i in range(0, len(hexd), 128))
    return ('\\pard\\qc\\fi0\\sb120\\sa40 {\\pict\\pngblip\\picw%d\\pich%d'
            '\\picwgoal%d\\pichgoal%d\n%s\n}\\par\n' % (w, h, goal_w, gh, lines))

# ================================================================== CONTENT
B = []   # body (two-column)

ABSTRACT_TEXT = ("Large language models now match or exceed conventional analysers on several "
    "classes of smart contract defect, but they are billed and bounded by the number of tokens "
    "they read. A deployed Solidity contract is mostly library code and boilerplate that cannot "
    "carry a vulnerability, so a large share of that budget is spent on text the model does not "
    "need. This paper presents AnchorSlice, a static pre-processing stage that reduces a contract "
    "to the fragments capable of hosting each vulnerability class before the source is shown to a "
    "model. AnchorSlice is entirely lexical: regular expressions and brace matching decide what "
    "survives, so the filter itself consumes no model capacity. Anchored lines are expanded to "
    "their enclosing statement blocks, overlapping regions are merged once and tagged with the "
    "categories they may host, and unmodified library constructs are collapsed to stubs under a "
    "rescue rule that preserves evidence. On the DIVE benchmark the filter retains 60.2% of source "
    "characters while keeping evidence for all 119 labelled category instances. In a paired A/B "
    "evaluation of 50 contracts with Claude Opus 5, AnchorSlice reduced token consumption by 56.6% "
    "and end-to-end latency by 19.7%, and improved detection quality on every aggregate measure: "
    "recall rose from 47.9% to 63.0%, F1 from 42.7% to 50.0%, and Cohen kappa from 0.145 to 0.220. "
    "The results indicate that aggressive, taxonomy-aware input reduction is compatible with, and "
    "can be beneficial to, LLM-based contract auditing.")

KEYWORDS_TEXT = ("smart contract security, large language models, program slicing, static analysis, "
          "token efficiency, vulnerability detection, DASP")


# ---- Abstract
ITEMS.append(('abstract', ABSTRACT_TEXT))
B.append('\\pard\\qj\\fi200\\sb60\\sa60\\f0\\fs18\\b\\i Abstract\\u8212?\\b0\\i0 '
    + esc("Large language models now match or exceed conventional analysers on several "
    "classes of smart contract defect, but they are billed and bounded by the number of tokens "
    "they read. A deployed Solidity contract is mostly library code and boilerplate that cannot "
    "carry a vulnerability, so a large share of that budget is spent on text the model does not "
    "need. This paper presents AnchorSlice, a static pre-processing stage that reduces a contract "
    "to the fragments capable of hosting each vulnerability class before the source is shown to a "
    "model. AnchorSlice is entirely lexical: regular expressions and brace matching decide what "
    "survives, so the filter itself consumes no model capacity. Anchored lines are expanded to "
    "their enclosing statement blocks, overlapping regions are merged once and tagged with the "
    "categories they may host, and unmodified library constructs are collapsed to stubs under a "
    "rescue rule that preserves evidence. On the DIVE benchmark the filter retains 60.2% of source "
    "characters while keeping evidence for all 119 labelled category instances. In a paired A/B "
    "evaluation of 50 contracts with Claude Opus 5, AnchorSlice reduced token consumption by 56.6% "
    "and end-to-end latency by 19.7%, and improved detection quality on every aggregate measure: "
    "recall rose from 47.9% to 63.0%, F1 from 42.7% to 50.0%, and Cohen kappa from 0.145 to 0.220. "
    "The results indicate that aggressive, taxonomy-aware input reduction is compatible with, and "
    "can be beneficial to, LLM-based contract auditing.")
    + '\\par\n')
ITEMS.append(('keywords', KEYWORDS_TEXT))
B.append('\\pard\\qj\\fi200\\sb60\\sa120\\f0\\fs18\\b\\i Keywords\\u8212?\\b0\\i0 '
    + esc("smart contract security, large language models, program slicing, static analysis, "
          "token efficiency, vulnerability detection, DASP") + '\\par\n')

# ---- I. INTRODUCTION
B.append(H1('I', 'Introduction'))
B.append(P("Smart contracts turn contractual clauses into code that executes without a trusted "
    "intermediary [1], and on Ethereum they hold and move assets directly [2]. That property is "
    "also the problem. A contract is immutable once deployed, its bytecode is public, and any "
    "defect in it is permanently reachable by an adversary who can read the source. The 2016 DAO "
    "incident, in which a reentrancy fault drained roughly sixty million dollars, made this "
    "concrete and motivated the first generation of automated analysers [3]. Practitioners "
    "subsequently organised the recurring fault patterns into the Decentralized Application "
    "Security Project (DASP) Top 10 [4], which remains the vocabulary most detection work is "
    "evaluated against.", first=False))
B.append(P("A decade of tooling has not settled the problem. When nine widely used analysers were "
    "run over 47,587 deployed contracts, they collectively identified only a minority of the "
    "annotated faults and flagged 97% of the corpus as vulnerable, which points to a false "
    "positive rate that makes unattended use impractical [5]. Controlled bug injection reaches the "
    "same conclusion from the opposite direction: injected faults of well understood shapes go "
    "undetected by tools designed specifically to find them [6]. The difficulty is not that "
    "analysers such as Slither [7] reason poorly about control flow, but that many real defects "
    "are semantic. Whether a missing modifier matters depends on what the function does, and no "
    "fixed data flow pattern captures that. Learning-based detectors were introduced partly to "
    "close this gap [8]."))
B.append(P("Large language models changed the trade-off again. Because they carry general "
    "knowledge of programming idioms and of security reasoning, they can be asked about a "
    "contract directly, without a hand-written rule for each fault class. Systems that pair a "
    "model with static confirmation [9], that split auditing into adversarial generation and "
    "criticism [10], or that fine-tune a detector and then argue about its output through "
    "cooperating agents [11] all report detection quality beyond what pattern-based tools "
    "achieve, and a recent systematic review counts a rapidly growing body of such work [12]."))
B.append(P("This capability has a cost that scales with input length. A model is billed per token "
    "and bounded by a context window, and long inputs also degrade reasoning: accuracy falls when "
    "the relevant evidence sits in the middle of a long prompt rather than near its edges [13]. "
    "For contract auditing the waste is easy to see. A fixed-supply ERC-20 token is several "
    "hundred lines of OpenZeppelin boilerplate wrapped around perhaps thirty lines that could "
    "plausibly hold a flaw, yet the whole file is submitted. Work on prompt compression has "
    "attacked the general version of this problem by using a small model to drop low-information "
    "tokens [14], but that approach is domain-agnostic and offers no guarantee that "
    "security-relevant code survives."))
B.append(P("We take the opposite route and exploit the fact that vulnerability classes have "
    "lexical footprints. A reentrancy fault requires an external call; a bad randomness fault "
    "requires a block-derived value; an arithmetic fault requires an operator. Code containing "
    "none of these cannot host the corresponding defect, and deciding that requires no model. "
    "This paper introduces AnchorSlice, a purely static pre-processing stage that keeps, for each "
    "DASP category, only the regions whose tokens make the category possible, and hands the model "
    "a compact annotated slice instead of the full file. We evaluate it against the DIVE "
    "multi-label benchmark [15], whose 22,330 contracts are annotated for the eight DASP "
    "categories we target. The design borrows the intuition of program slicing [16] but "
    "deliberately stops short of dependence analysis, so that the filter runs in milliseconds and "
    "never needs to compile."))
B.append(P("This paper makes three contributions. First, we define an anchor set for the eight "
    "DASP categories together with a merge procedure that emits each source region once and "
    "labels it with every category it may host, which keeps the slice compact when categories "
    "overlap. Second, we validate the filter against DIVE and show that it retains evidence for "
    "all 119 labelled category instances while emitting 60.2% of the original characters. Third, "
    "we report a paired A/B evaluation in which slicing cut token consumption by 56.6% and "
    "latency by 19.7% while improving recall, F1 and agreement, and we analyse which anchors "
    "carried useful information and which did not."))

# ---- II. RELATED WORK
B.append(H1('II', 'Related Work'))
B.append(H2('A. Program Analysis for Smart Contract Security'))
B.append(P("Oyente introduced symbolic execution of EVM bytecode and defined several of the fault "
    "patterns still in use [3]. Securify derived compliance and violation patterns from "
    "dependence graphs to make its verdicts explainable [17], while SmartCheck worked on an "
    "intermediate XML representation of Solidity to keep analysis lightweight [18]. Mythril "
    "combined symbolic execution with taint analysis over bytecode [19], and MAIAN targeted "
    "trace-level properties such as contracts that can be made to leak or lock funds [20]. "
    "VeriSmart pushed precision further for arithmetic safety by inferring transaction invariants "
    "[21]. Dynamic approaches complement these: ContractFuzzer generated transaction sequences "
    "against an instrumented EVM [22], and sFuzz added an adaptive strategy for branches that "
    "random input rarely reaches [23]. Slither occupies a middle ground, converting Solidity to "
    "an SSA-based intermediate form that supports fast detectors and code review aids [7]. The "
    "large-scale comparisons of these tools [5] and the injection studies that probe them [6] "
    "both conclude that coverage remains partial and precision low, which is the gap "
    "learning-based and model-based methods have tried to close.", first=False))
B.append(H2('B. Learning-Based Vulnerability Detection'))
B.append(P("VulDeePecker showed that vulnerability detection could be learned from code gadgets, "
    "slices of semantically related statements gathered around library and API calls [24]. SySeVR "
    "generalised the idea to four syntactic seed types and used program dependence graphs for "
    "slicing [25]. Devign moved to graph representations that combine abstract syntax, control "
    "flow and data flow [26], and LineVul demonstrated that transformer models can localise "
    "predictions to individual lines [27], often building on code-specific pre-training such as "
    "CodeBERT [28]. In the contract setting, Zhuang et al. represented functions as normalised "
    "graphs and applied a degree-free graph convolutional network and a temporal message "
    "propagation network [8]; later work combined such graph models with expert-designed patterns "
    "to improve interpretability [29]. AnchorSlice is related to this literature mainly through "
    "the seed-and-expand idea: like VulDeePecker and SySeVR we begin from syntactic anchors, but "
    "we produce a prompt for a general-purpose model rather than a feature vector for a trained "
    "classifier, and we therefore need no dependence graph.", first=False))
B.append(H2('C. Large Language Models for Smart Contract Auditing'))
B.append(P("Code-trained models [30] and the emergence of in-context learning [31] and "
    "chain-of-thought prompting [32] made it practical to ask a general model for a security "
    "judgement. GPTScan pairs GPT with static confirmation, using the model to nominate candidate "
    "variables and statements and dedicated modules to validate them, and reports recall above "
    "70% on ground-truth logic bugs [9]. GPTLens splits the task between an auditor role that "
    "proposes vulnerabilities and a critic role that scores them, which suppresses the model's "
    "tendency to over-report [10]. LLM4Vuln decouples the components of vulnerability reasoning "
    "so that knowledge retrieval, tool use and reasoning can be measured separately [33]. "
    "LLM-SmartAudit organises multiple agents around a conversation about the contract [34], and "
    "Smart-LLaMA post-trains an open model in two stages to produce both a decision and an "
    "explanation [35]. iAudit fine-tunes a detector and a reasoner and then has ranker and critic "
    "agents debate the cause, reaching an F1 of 91.21% on a curated set of 263 vulnerabilities "
    "[11]. PropertyGPT goes further and generates formal properties for verification rather than "
    "verdicts alone [36]. What these systems share is an assumption that the model receives the "
    "contract; the systematic review of the area notes that context length is a recurring "
    "constraint [12]. Our work is orthogonal to all of them, since any of these pipelines could "
    "consume a sliced contract instead of a whole one.", first=False))
B.append(H2('D. Context Reduction for Long-Input Inference'))
B.append(P("The cost of long prompts has been attacked generically. LLMLingua uses a small "
    "language model to identify and drop low-information tokens, reporting high compression with "
    "limited loss [14], and LongLLMLingua adds question-aware reordering for long-context settings "
    "[37]. Retrieval-augmented generation avoids the problem by fetching only relevant passages "
    "[38]. These methods estimate relevance statistically and therefore cannot promise that a "
    "particular security-critical line survives. Classical program slicing offers the opposite "
    "guarantee, computing the statements that can affect a criterion [16], and thin slicing "
    "restricts the result to statements that produce the value of interest [39]. Full slicing "
    "needs a compilable program and a dependence graph, which is a strong requirement for a "
    "corpus of deployed contracts spanning many compiler versions. AnchorSlice sits between these "
    "positions: it is coarser than dependence-based slicing, but its criterion is the "
    "vulnerability taxonomy itself and its recall against a labelled benchmark can be measured "
    "directly.", first=False))
B.append(H2('E. Benchmarks and Labelled Datasets'))
B.append(P("Evaluation in this area depends on the quality of labels. ScrawlD labelled real "
    "contracts by majority vote over five analysers [40], and DAppSCAN built large source and "
    "bytecode datasets from 1,199 audit reports covering 682 DApp projects [41]. We use DIVE [15], "
    "which annotates 22,330 contracts deployed between 2016 and 2024 against the eight DASP "
    "categories. DIVE aggregates MAIAN, Mythril, Semgrep, Slither, Solhint and VeriSmart through "
    "a power-based voting scheme and then re-checks positive findings against category-specific "
    "code evidence, a post-hoc validation that corrected about 14.3% of DoS and 24.9% of time "
    "manipulation labels. Labels are assigned at contract level, which shapes how filter recall "
    "can be validated.", first=False))

# ---- III. APPROACH
B.append(H1('III', 'The AnchorSlice Approach'))
B.append(H2('A. Design Goals'))
B.append(P("Two requirements shaped the design. The filter must be fully static, in the sense "
    "that every decision follows from regular expressions and brace counting; a filter that "
    "needed model judgement to decide what to keep would spend the budget it is meant to save. "
    "It must also emit each region of source at most once. Running eight independent "
    "category-specific passes would be the obvious construction, but the passes overlap heavily "
    "and their union would exceed the original file. AnchorSlice therefore performs a single pass "
    "and attaches a set of candidate categories to each emitted region.", first=False))
B.append(H2('B. Lexical Anchors and the Visibility Gate'))
B.append(P("Each category owns a set of anchor expressions, and a line matching one marks its "
    "enclosing region as a candidate for that category. Two macros carry most of the weight. EXT "
    "matches any external or cross-contract call, including low-level call, send, transfer, "
    "delegatecall and staticcall forms, calls through an interface cast, and calls on a receiver "
    "that is not a language builtin. MUTFN matches any public or external function that is not "
    "declared view or pure. The second macro deserves comment. Access control faults are often an "
    "absence rather than a presence, so no positive pattern can find them; treating every "
    "state-mutating entry point as a candidate is the only static way to surface a contract whose "
    "fault is a missing modifier.", first=False))
B.append(P("We evaluated five semantic gates intended to suppress obviously safe regions and "
    "retained one. Suppressing arithmetic candidates in contracts compiled under Solidity 0.8, "
    "where overflow reverts by default, cut arithmetic recall from 1.00 to 0.43, because DIVE "
    "labels many such contracts positive regardless. Requiring a state write before admitting a "
    "reentrancy candidate cut its recall from 0.91 to 0.36. Treating a call wrapped in require as "
    "a checked return cut that category from 0.60 to 0.20. Only the visibility gate survived: a "
    "view or pure body cannot mutate state, and excluding such bodies from the five state-"
    "dependent categories cost no recall at all. The rejected gates were sound as Solidity "
    "reasoning but disagreed with the benchmark's annotation policy, which is a useful reminder "
    "that a filter tuned to a dataset inherits that dataset's conventions. Table I gives the "
    "complete anchor set for the eight categories, the gate retained for each, and the recall "
    "the resulting filter achieves against the benchmark."))
B.append(wide_start())
B.append(tblhead('Table I.  Anchor Specification for the Eight DASP Categories'))
B.append(table([
    ['Category', 'Anchor expressions', 'Gate', 'Recall'],
    ['Reentrancy', 'EXT', 'view / pure', '22 / 22'],
    ['Access Control',
     'modifier  · only\\w+  · owner =  · tx.origin  · selfdestruct  · suicide  · '
     'delegatecall  · require(msg.sender  · renounce  · transferOwnership  · admin  · MUTFN',
     'view / pure', '39 / 39'],
    ['Arithmetic',
     '[+ - * / %]=  · ++  · --  · x [+ * / %] y  · x - y  · **  · << >>  · unchecked',
     '—', '23 / 23'],
    ['Unchecked Return Values', 'EXT', 'view / pure', '5 / 5'],
    ['DoS',
     'for(  · while(  · .push(  · .length  · require(  · revert  · assert(  · EXT',
     'view / pure', '7 / 7'],
    ['Bad Randomness',
     'blockhash  · block.{difficulty, coinbase, gaslimit, number, timestamp, prevrandao}  · now  · '
     'keccak256  · sha3  · sha256  · random  · nonce  · seed',
     '—', '5 / 5'],
    ['Front Running',
     'approve(  · allowance  · msg.value  · tx.gasprice  · price  · bid  · swap*(  · '
     'slippage  · amountOutMin  · deadline  · reserve  · MUTFN',
     'view / pure', '5 / 5'],
    ['Time manipulation',
     'now  · block.timestamp  · block.number  · N days|hours|minutes|weeks  · deadline  · '
     'startTime  · endTime  · cooldown  · lastClaim  · timeout',
     '—', '13 / 13'],
    ['All categories', '—', '—', '119 / 119'],
], [1700, 7800, 8700, 9600]))
B.append(caption('EXT matches any external or cross-contract call: .call, .call.value, .send, .transfer, '
    'delegatecall, staticcall, a call through an interface cast, and a call on any receiver that is not a '
    'language builtin. MUTFN matches any public or external function not declared view or pure. The gate '
    'column names the only semantic restriction retained after ablation. Recall is the number of '
    'label-positive contracts that keep at least one block tagged with the category.'))
B.append(wide_end())

B.append(H2('C. Window Extraction and Tag-Preserving Merge'))
B.append(P("An anchored line is expanded to the innermost brace block that contains it, capped at "
    "ten lines; past that cap the window falls back to the anchor with two lines of context on "
    "each side. The enclosing function signature is attached separately so that visibility and "
    "modifiers stay visible even when the body is truncated. Windows are then sorted and merged: "
    "any two whose ranges overlap or abut become a single block whose tag set is the union of "
    "theirs. A region relevant to both reentrancy and arithmetic is consequently emitted once and "
    "carries both labels, which is what keeps the single-emission property. Across the evaluation "
    "corpus this produces 14.9 blocks per contract.", first=False))
B.append(H2('D. Library Collapse and Recall-Preserving Rescue'))
B.append(P("Unmodified reference implementations account for a large share of a typical file. "
    "AnchorSlice detects top-level SafeMath, Address, Context, Ownable, ERC20 and common exchange "
    "interfaces by name and replaces each with a one-line stub, so the model still knows the "
    "construct is present. Applied naively this cost recall, dropping access control to 0.95 and "
    "DoS to 0.86, because in a few contracts the only anchor for a category lay inside a "
    "collapsed construct. A rescue pass repairs the loss: if a category ends the pass with no "
    "block anywhere in the file while an anchor for it exists inside collapsed text, a three-line "
    "window is emitted at that anchor. The rescue restores recall to 1.00 for about two "
    "percentage points of size.", first=False))
B.append(H2('E. Slice Rendering'))
B.append(P("The emitted document begins with the stubs for collapsed libraries and the "
    "contract-level declarations, then lists the blocks in source order. Each block carries a "
    "header naming its original line range and its candidate categories, for example a block "
    "spanning lines 37 to 60 marked as a candidate for access control, arithmetic and reentrancy. "
    "Line numbers refer to the original file so that a finding can be traced back. The prompt "
    "explains that these tags are lexical hints rather than findings and that most tagged blocks "
    "are not vulnerable. A guard handles small files: when the block headers would cost more than "
    "the removed lines save, the contract is sent whole with comments stripped, which occurred "
    "for 11 of the 50 contracts in our sample.", first=False))
B.append('\\sect\\sectd\\sbknone\\cols1\\linex0\n')
B.append(picture(os.path.join(HERE, 'fig1_pipeline.png'), 9600))
B.append(caption("Fig. 1.  The two experimental arms. Only the three highlighted stages differ; "
                 "model, prompt, sampling and decoding settings are identical."))
B.append('\\sect\\sectd\\sbknone\\cols2\\colsx397\\linex0\n')

# ---- IV. EXPERIMENTAL SETUP
B.append(H1('IV', 'Experimental Setup'))
B.append(H2('A. Dataset and Sampling'))
B.append(P("We drew 50 contracts from DIVE [15] using a seeded random sample repaired so that "
    "every category has at least five positive and five negative instances, which keeps base "
    "rates near the corpus prevalence while making all eight categories measurable in both "
    "directions. The sample totals 552,043 characters, with a median contract of 11,484 "
    "characters and a maximum of 27,687, so no contract required truncation. Compiler versions "
    "split 27 legacy against 23 at Solidity 0.8 or above. The 400 label cells contain 119 "
    "positives, a positive rate of 29.8%.", first=False))
B.append(H2('B. Model and Prompt Configuration'))
B.append(P("Both arms query Claude Opus 5 at high reasoning effort through a headless interface "
    "with all tools disabled, so the model sees nothing beyond the prompt and cannot retrieve the "
    "answer. A JSON schema constrains the reply to eight binary labels with per-category "
    "confidences and short justifications. The system prompt defines each DASP category with a "
    "minimal code example and instructs the model to report a fault only where it is reachable "
    "rather than wherever a pattern appears.", first=False))
B.append(H2('C. A/B Protocol'))
B.append(P("Arm A submits the complete source. Arm B submits the AnchorSlice output preceded by a "
    "short explanation of the block format. Everything else is held constant: same model, same "
    "effort, same system prompt, same schema, same contracts, one call each. Because both arms "
    "classify the same 400 cells the comparison is paired, and we report McNemar's exact test on "
    "discordant cells alongside the aggregate measures.", first=False))
B.append(H2('D. Metrics'))
B.append(P("We report label agreement over all cells, Hamming loss, exact match at the contract "
    "level, and micro-averaged precision, recall and F1. Because the label distribution is "
    "unbalanced we also report Cohen's kappa, which corrects for agreement expected by chance. "
    "Resource use is measured as total tokens across all classes, wall-clock time, and cost.", first=False))

# ---- V. RESULTS
B.append(H1('V', 'Results'))
B.append(H2('A. Slice Compactness and Anchor Recall'))
B.append(P("AnchorSlice reduced the corpus from 552,043 to 332,134 characters, or 60.2% of the "
    "original, with a mean per-contract reduction of 34.0%. Recall was 1.00 for every category: "
    "all 119 label-positive category instances retained at least one block tagged with that "
    "category, as summarised in Table I. Decomposing the pipeline shows that comment removal "
    "brings the corpus to 76.3% and library collapse to 56.0%, with the anchoring stage returning "
    "60.2% after its block headers are counted.", first=False))
B.append(H2('B. Token Consumption and Latency'))
B.append(P("Table II reports resource use. Slicing cut total token consumption from 913,958 to "
    "396,438, a reduction of 56.6%, and mean consumption per contract from 18,279 to 7,928 "
    "tokens. Wall-clock time fell from 1,019.6 to 818.5 seconds, or 19.7%, which matters for "
    "throughput when the corpus is scaled beyond a sample. Output tokens fell 15.6%, a smaller "
    "proportion than the input reduction because the length of the model's reasoning is governed "
    "by the eight decisions it must make rather than by how much source it reads. Cost decreased "
    "by 1.4%.", first=False))
B.append(tblhead('Table II.  Resource Consumption Across 50 Contracts'))
B.append(table([
    ['Measure', 'Arm A', 'Arm B', 'Change'],
    ['Input tokens', '204', '102', '-50.0%'],
    ['Output tokens', '63,798', '53,872', '-15.6%'],
    ['Cache write', '125,385', '176,438', '+40.7%'],
    ['Cache read', '724,571', '166,026', '-77.1%'],
    ['Total tokens', '913,958', '396,438', '-56.6%'],
    ['Tokens / contract', '18,279', '7,928', '-56.6%'],
    ['Wall clock (s)', '1,019.6', '818.5', '-19.7%'],
    ['Seconds / contract', '20.4', '16.4', '-19.7%'],
    ['Cost (USD)', '3.4103', '3.3636', '-1.4%'],
], [1800, 2650, 3500, 4400]))
B.append(H2('C. Detection Effectiveness'))
B.append(P("Detection quality improved on every aggregate measure, as Table III shows. Recall "
    "rose from 47.9% to 63.0%, an absolute gain of 15.1 percentage points, and precision rose "
    "from 38.5% to 41.4%, so the additional detections were not obtained by indiscriminate "
    "over-reporting. F1 improved from 42.7% to 50.0% and Cohen's kappa from 0.145 to 0.220, a "
    "relative gain of 51.7%. Label agreement rose from 61.8% to 62.5% and Hamming loss fell "
    "correspondingly. Two contracts were classified perfectly across all eight categories under "
    "slicing, where the baseline achieved none.", first=False))
B.append(P("The confusion matrix locates the change. False negatives fell from 62 to 44 while "
    "true positives rose from 57 to 75, against an increase in false positives from 91 to 106. "
    "At the contract level 14 contracts improved, 23 were unchanged and 13 regressed. The gain is "
    "therefore concentrated in recovering faults the baseline missed rather than in eliminating "
    "spurious reports."))
B.append(tblhead("Table III.  Detection Effectiveness Over 400 Label Cells"))
B.append(table([
    ['Metric', 'Arm A', 'Arm B', 'Change'],
    ['Label agreement', '61.8%', '62.5%', '+0.7 pp'],
    ['Hamming loss', '38.2%', '37.5%', '-0.8 pp'],
    ['Exact match (8/8)', '0 / 50', '2 / 50', '+2'],
    ['Precision', '38.5%', '41.4%', '+2.9 pp'],
    ['Recall', '47.9%', '63.0%', '+15.1 pp'],
    ['F1', '42.7%', '50.0%', '+7.3 pp'],
    ['Cohen kappa', '0.145', '0.220', '+0.075'],
    ['True positives', '57', '75', '+18'],
    ['False negatives', '62', '44', '-18'],
], [1800, 2650, 3500, 4400]))
B.append(H2('D. Per-Category Behaviour'))
B.append(P("Table IV reports every category and Fig. 2 shows the three that improved. Access "
    "control gained 14.0 percentage points, by far the largest movement, and is also the category where "
    "the baseline was weakest, marking only 6 of 39 positives. The MUTFN anchor tags precisely the "
    "state-mutating entry points where a missing modifier would live, and under slicing the model "
    "identified 11 more, cutting false negatives from 33 to 24 at a cost of two false positives. Front "
    "running gained 6.0 points and eliminated both of its false negatives, and reentrancy gained 4.0 "
    "points while reducing false negatives from four to one. Unchecked return values and time "
    "manipulation held their agreement, and the former halved its false negatives, so six of the eight "
    "categories either improved or held. Arithmetic and bad randomness each moved back by 2.0 points, "
    "and DoS by 14.0 points, which we attribute to an over-broad anchor in Section VI.", first=False))
B.append(picture(os.path.join(HERE, 'fig2_per_category.png'), 9600))
B.append(caption("Fig. 2.  Label agreement before and after slicing for the three categories "
                 "where agreement improved. Table IV reports all eight categories."))
B.append('\\sect\\sectd\\sbknone\\cols2\\colsx397\\linex0\n')

# ---- VI. DISCUSSION
B.append(wide_start())
B.append(tblhead('Table IV.  Per-Category Detection Detail Across All Eight DASP Categories'))
B.append(table([
    ['Category', 'DIVE +', 'LLM + A', 'LLM + B', 'Agree A', 'Agree B', 'Change', 'FN A', 'FN B'],
    ['Reentrancy', '22', '23', '27', '0.820', '0.860', '+4.0', '4', '1'],
    ['Access Control', '39', '6', '17', '0.340', '0.480', '+14.0', '33', '24'],
    ['Arithmetic', '23', '17', '22', '0.560', '0.540', '-2.0', '14', '12'],
    ['Unchecked Return Values', '5', '12', '16', '0.700', '0.700', '0.0', '4', '2'],
    ['DoS', '7', '13', '20', '0.760', '0.620', '-14.0', '3', '3'],
    ['Bad Randomness', '5', '3', '4', '0.960', '0.940', '-2.0', '2', '2'],
    ['Front Running', '5', '46', '47', '0.100', '0.160', '+6.0', '2', '0'],
    ['Time manipulation', '13', '28', '28', '0.700', '0.700', '0.0', '0', '0'],
    ['All categories', '119', '148', '181', '0.618', '0.625', '+0.7', '62', '44'],
], [2400, 3300, 4200, 5100, 6100, 7100, 8000, 8800, 9600]))
B.append(caption('DIVE + counts ground-truth positives; LLM + counts contracts the model marked positive; '
    'FN counts false negatives. Change is the shift in label agreement in percentage points.'))
B.append(wide_end())

B.append(H1('VI', 'Discussion'))
B.append(H2('A. Why Removing Code Preserves Detection Signal'))
B.append(P("The central empirical observation is that discarding roughly 40% of the source "
    "characters did not degrade the model's judgement, and on aggregate measures improved it. The "
    "simplest reading is that the removed text was not being used. Comment blocks, licence "
    "headers and unmodified library implementations carry no information a security judgement "
    "depends on, and the model appears to treat them accordingly. This is consistent with the "
    "observation that relevant evidence buried inside long inputs is attended to less reliably "
    "than evidence near the edges [13]: shortening the input raises the density of "
    "security-relevant material and shortens the distance between related fragments.", first=False))
B.append(H2('B. Anchor Tags as a Localisation Prior'))
B.append(P("The stage decomposition shows that comment removal and library collapse account for "
    "essentially the whole size reduction, while the anchoring stage removes 22.3% of the "
    "remaining source and adds 16.9% back as block headers. The value of anchoring therefore lies "
    "less in compression than in localisation: the tags tell the model where each category could "
    "plausibly live. Access control is the clearest case. It is the hardest category for the "
    "baseline precisely because its faults are absences, and a tag that marks every state-"
    "mutating entry point supplies exactly the prior the model lacks. This suggests a design "
    "principle, that an anchor is useful in proportion to how selective it is.", first=False))
B.append(H2('C. Risks and Limitations'))
B.append(P("The aggregate improvements are not statistically significant. McNemar's exact test "
    "over the 400 paired cells gives 20 cells correct only under the baseline against 23 correct "
    "only under slicing, for a two-sided p of 0.761. The observed gains in recall and F1 should "
    "therefore be read as encouraging rather than established, and the claim the experiment "
    "supports firmly is that slicing does not harm detection while more than halving token use.", first=False))
B.append(P("The monetary saving is much smaller than the token saving. Cost fell 1.4% against a "
    "56.6% token reduction because the reduction falls almost entirely on cached input, the "
    "cheapest token class, while output tokens barely moved. Deployments whose pricing weights "
    "these classes differently will see a different figure, so token count and latency are the "
    "more portable benefits.", first=False))
B.append(P("One anchor is clearly mis-specified. The DoS anchor includes require, revert and "
    "assert, which appear in nearly every non-trivial function, so almost every block carries a "
    "DoS tag. The model read that ubiquity as evidence and raised its positive count from 13 to "
    "20 against a ground truth of 7, without recovering any false negative. A tag that fires "
    "almost everywhere carries no information yet still shifts the model's prior.", first=False))
B.append(P("The treatment mixes two changes. Arm B both removes code and adds category tags, and "
    "the DoS result suggests these can act in opposite directions, so the aggregate outcome may "
    "understate the benefit of removal alone. A tag-free arm is needed to separate them.", first=False))
B.append(P("Filter recall is validated against a weak criterion. DIVE labels contracts rather "
    "than lines, so recall of 1.00 means only that a positive contract keeps some block tagged "
    "with that category, not that it keeps the specific statements an annotator had in mind.", first=False))
B.append(P("Finally, the anchors were developed by iterating against the same 50 contracts used "
    "for evaluation, so the recall figure is an in-sample fit and will be optimistic on held-out "
    "data. The sample is also small and each arm was run once, so part of the discordance between "
    "arms reflects the model's own non-determinism.", first=False))

# ---- VII. CONCLUSION
B.append(H1('VII', 'Conclusion and Future Work'))
B.append(P("We presented AnchorSlice, a static pre-processing stage that reduces a Solidity "
    "contract to the fragments capable of hosting each DASP category before the source reaches a "
    "language model. The filter is lexical throughout, needs no compilation, and retained "
    "evidence for all 119 labelled category instances in our sample while emitting 60.2% of the "
    "original characters. In a paired A/B evaluation with Claude Opus 5 it reduced token "
    "consumption by 56.6% and latency by 19.7% while improving recall from 47.9% to 63.0%, F1 "
    "from 42.7% to 50.0% and Cohen's kappa from 0.145 to 0.220.", first=False))
B.append(P("Three directions follow. A tag-free arm would separate the effect of removing code "
    "from the effect of naming candidate categories, and would also remove the header overhead "
    "that currently offsets the anchoring stage. A selectivity threshold that suppresses any "
    "category tagging more than a set fraction of a contract's blocks would address the DoS "
    "failure directly while preserving the access control gain. Finally, the anchors should be "
    "re-validated on a held-out DIVE split, and the protocol repeated across several runs, before "
    "the approach is applied to the full corpus."))

# ---- REFERENCES
REFS = [
 "N. Szabo, \u201cFormalizing and securing relationships on public networks,\u201d First Monday, vol. 2, no. 9, 1997.",
 "G. Wood, \u201cEthereum: A secure decentralised generalised transaction ledger,\u201d Ethereum Project Yellow Paper, 2014.",
 "L. Luu, D.-H. Chu, H. Olickel, P. Saxena, and A. Hobor, \u201cMaking smart contracts smarter,\u201d in Proc. ACM SIGSAC Conf. Computer and Communications Security (CCS), 2016, pp. 254\u2013269.",
 "NCC Group, \u201cDecentralized Application Security Project (DASP) Top 10,\u201d 2018. [Online]. Available: https://dasp.co",
 "T. Durieux, J. F. Ferreira, R. Abreu, and P. Cruz, \u201cEmpirical review of automated analysis tools on 47,587 Ethereum smart contracts,\u201d in Proc. ACM/IEEE Int. Conf. Software Engineering (ICSE), 2020, pp. 530\u2013541.",
 "A. Ghaleb and K. Pattabiraman, \u201cHow effective are smart contract analysis tools? Evaluating smart contract static analysis tools using bug injection,\u201d in Proc. ACM SIGSOFT Int. Symp. Software Testing and Analysis (ISSTA), 2020, pp. 415\u2013427.",
 "J. Feist, G. Grieco, and A. Groce, \u201cSlither: A static analysis framework for smart contracts,\u201d in Proc. IEEE/ACM Int. Workshop on Emerging Trends in Software Engineering for Blockchain (WETSEB), 2019, pp. 8\u201315.",
 "Y. Zhuang, Z. Liu, P. Qian, Q. Liu, X. Wang, and Q. He, \u201cSmart contract vulnerability detection using graph neural network,\u201d in Proc. Int. Joint Conf. Artificial Intelligence (IJCAI), 2020, pp. 3283\u20133290.",
 "Y. Sun, D. Wu, Y. Xue, H. Liu, H. Wang, Z. Xu, X. Xie, and Y. Liu, \u201cGPTScan: Detecting logic vulnerabilities in smart contracts by combining GPT with program analysis,\u201d in Proc. IEEE/ACM Int. Conf. Software Engineering (ICSE), 2024, pp. 1\u201313.",
 "S. Hu, T. Huang, F. \u0130lhan, S. F. Tekin, and L. Liu, \u201cLarge language model-powered smart contract vulnerability detection: New perspectives,\u201d in Proc. IEEE Int. Conf. Trust, Privacy and Security in Intelligent Systems and Applications (TPS-ISA), 2023, pp. 297\u2013306.",
 "W. Ma, D. Wu, Y. Sun, T. Wang, S. Liu, J. Zhang, Y. Xue, and Y. Liu, \u201cCombining fine-tuning and LLM-based agents for intuitive smart contract auditing with justifications,\u201d in Proc. IEEE/ACM Int. Conf. Software Engineering (ICSE), 2025, pp. 1\u201313.",
 "Z. He, Z. Li, S. Yang, A. Qiao, X. Zhang, X. Luo, and T. Chen, \u201cLarge language models for blockchain security: A systematic literature review,\u201d arXiv:2403.14280, 2024.",
 "N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, \u201cLost in the middle: How language models use long contexts,\u201d Trans. Assoc. Computational Linguistics, vol. 12, pp. 157\u2013173, 2024.",
 "H. Jiang, Q. Wu, C.-Y. Lin, Y. Yang, and L. Qiu, \u201cLLMLingua: Compressing prompts for accelerated inference of large language models,\u201d in Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP), 2023, pp. 13358\u201313376.",
 "S. J. Alsunaidi, H. Aljamaan, and M. Hammoudeh, \u201cDIVE: A multi-label smart contract vulnerability dataset,\u201d Scientific Data, vol. 13, art. 664, 2026.",
 "M. Weiser, \u201cProgram slicing,\u201d in Proc. Int. Conf. Software Engineering (ICSE), 1981, pp. 439\u2013449.",
 "P. Tsankov, A. Dan, D. Drachsler-Cohen, A. Gervais, F. B\u00fcnzli, and M. Vechev, \u201cSecurify: Practical security analysis of smart contracts,\u201d in Proc. ACM SIGSAC Conf. Computer and Communications Security (CCS), 2018, pp. 67\u201382.",
 "S. Tikhomirov, E. Voskresenskaya, I. Ivanitskiy, R. Takhaviev, E. Marchenko, and Y. Alexandrov, \u201cSmartCheck: Static analysis of Ethereum smart contracts,\u201d in Proc. IEEE/ACM Int. Workshop on Emerging Trends in Software Engineering for Blockchain (WETSEB), 2018, pp. 9\u201316.",
 "ConsenSys, \u201cMythril: Security analysis tool for EVM bytecode,\u201d 2018. [Online]. Available: https://github.com/ConsenSys/mythril",
 "I. Nikoli\u0107, A. Kolluri, I. Sergey, P. Saxena, and A. Hobor, \u201cFinding the greedy, prodigal, and suicidal contracts at scale,\u201d in Proc. Annual Computer Security Applications Conf. (ACSAC), 2018, pp. 653\u2013663.",
 "S. So, M. Lee, J. Park, H. Lee, and H. Oh, \u201cVeriSmart: A highly precise safety verifier for Ethereum smart contracts,\u201d in Proc. IEEE Symp. Security and Privacy (S&P), 2020, pp. 1678\u20131694.",
 "B. Jiang, Y. Liu, and W. K. Chan, \u201cContractFuzzer: Fuzzing smart contracts for vulnerability detection,\u201d in Proc. ACM/IEEE Int. Conf. Automated Software Engineering (ASE), 2018, pp. 259\u2013269.",
 "T. D. Nguyen, L. H. Pham, J. Sun, Y. Lin, and Q. T. Minh, \u201csFuzz: An efficient adaptive fuzzer for Solidity smart contracts,\u201d in Proc. ACM/IEEE Int. Conf. Software Engineering (ICSE), 2020, pp. 778\u2013788.",
 "Z. Li, D. Zou, S. Xu, X. Ou, H. Jin, S. Wang, Z. Deng, and Y. Zhong, \u201cVulDeePecker: A deep learning-based system for vulnerability detection,\u201d in Proc. Network and Distributed System Security Symp. (NDSS), 2018.",
 "Z. Li, D. Zou, S. Xu, H. Jin, Y. Zhu, and Z. Chen, \u201cSySeVR: A framework for using deep learning to detect software vulnerabilities,\u201d IEEE Trans. Dependable and Secure Computing, vol. 19, no. 4, pp. 2244\u20132258, 2022.",
 "Y. Zhou, S. Liu, J. Siow, X. Du, and Y. Liu, \u201cDevign: Effective vulnerability identification by learning comprehensive program semantics via graph neural networks,\u201d in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2019, pp. 10197\u201310207.",
 "M. Fu and C. Tantithamthavorn, \u201cLineVul: A transformer-based line-level vulnerability prediction,\u201d in Proc. IEEE/ACM Int. Conf. Mining Software Repositories (MSR), 2022, pp. 608\u2013620.",
 "Z. Feng, D. Guo, D. Tang, N. Duan, X. Feng, M. Gong, L. Shou, B. Qin, T. Liu, D. Jiang, and M. Zhou, \u201cCodeBERT: A pre-trained model for programming and natural languages,\u201d in Findings of EMNLP, 2020, pp. 1536\u20131547.",
 "Z. Liu, P. Qian, X. Wang, Y. Zhuang, L. Qiu, and X. Wang, \u201cCombining graph neural networks with expert knowledge for smart contract vulnerability detection,\u201d IEEE Trans. Knowledge and Data Engineering, vol. 35, no. 2, pp. 1296\u20131310, 2023.",
 "M. Chen et al., \u201cEvaluating large language models trained on code,\u201d arXiv:2107.03374, 2021.",
 "T. B. Brown et al., \u201cLanguage models are few-shot learners,\u201d in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2020, pp. 1877\u20131901.",
 "J. Wei, X. Wang, D. Schuurmans, M. Bosma, B. Ichter, F. Xia, E. Chi, Q. Le, and D. Zhou, \u201cChain-of-thought prompting elicits reasoning in large language models,\u201d in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2022, pp. 24824\u201324837.",
 "Y. Sun, D. Wu, Y. Xue, H. Liu, W. Ma, L. Zhang, M. Shi, and Y. Liu, \u201cLLM4Vuln: A unified evaluation framework for decoupling and enhancing LLMs\u2019 vulnerability reasoning,\u201d arXiv:2401.16185, 2024.",
 "Z. Wei, J. Sun, Z. Zhang, X. Zhang, X. Yang, and L. Zhu, \u201cLLM-SmartAudit: Advanced smart contract vulnerability detection,\u201d arXiv:2410.09381, 2024.",
 "L. Yu, S. Chen, H. Yuan, P. Wang, Z. Huang, J. Zhang, C. Shen, F. Zhang, J. Yang, and J. Li, \u201cSmart-LLaMA: Two-stage post-training of large language models for smart contract vulnerability detection and explanation,\u201d arXiv:2411.06221, 2024.",
 "Y. Liu, Y. Xue, D. Wu, Y. Sun, Y. Li, M. Shi, and Y. Liu, \u201cPropertyGPT: LLM-driven formal verification of smart contracts through retrieval-augmented property generation,\u201d in Proc. Network and Distributed System Security Symp. (NDSS), 2025.",
 "H. Jiang, Q. Wu, X. Luo, D. Li, C.-Y. Lin, Y. Yang, and L. Qiu, \u201cLongLLMLingua: Accelerating and enhancing LLMs in long context scenarios via prompt compression,\u201d in Proc. Annual Meeting of the Association for Computational Linguistics (ACL), 2024, pp. 1658\u20131677.",
 "P. Lewis et al., \u201cRetrieval-augmented generation for knowledge-intensive NLP tasks,\u201d in Proc. Advances in Neural Information Processing Systems (NeurIPS), 2020, pp. 9459\u20139474.",
 "M. Sridharan, S. J. Fink, and R. Bod\u00edk, \u201cThin slicing,\u201d in Proc. ACM SIGPLAN Conf. Programming Language Design and Implementation (PLDI), 2007, pp. 112\u2013122.",
 "S. S. Yashavant, S. Kumar, and A. Karkare, \u201cScrawlD: A dataset of real world Ethereum smart contracts labelled with vulnerabilities,\u201d arXiv:2202.11409, 2022.",
 "Z. Zheng, J. Su, J. Chen, D. Lo, Z. Zhong, and M. Ye, \u201cDAppSCAN: Building large-scale datasets for smart contract weaknesses in DApp projects,\u201d IEEE Trans. Software Engineering, vol. 50, no. 6, pp. 1360\u20131373, 2024.",
]
B.append(H5('References'))
ITEMS.append(('refs', REFS))
for i, r in enumerate(REFS, 1):
    B.append('\\pard\\qj\\fi-260\\li260\\sb0\\sa30\\f0\\fs16 [%d]\\tab %s\\par\n' % (i, esc(r)))

# ================================================================== ASSEMBLE
TITLE = ("AnchorSlice: Anchor-Guided Static Slicing for Token-Efficient Smart Contract "
         "Vulnerability Detection with Large Language Models")
AUTHORS = [("Sajad Aghanasiri", "sajad.aghanasiri@example.com"),
           ("Sina Zaker",       "sina.zaker@example.com"),
           ("Alireza Shameli-Sendi", "a_shameli@sbu.ac.ir")]

head = []
head.append('\\pard\\qc\\fi0\\sb0\\sa180\\f0\\fs36\\b %s\\par\n' % esc(TITLE))
# author row: 3 equal cells
head.append('\\trowd\\trgaph40\\trleft0')
for w in (3100, 6200, 9300):
    head.append('\\clvertalt\\cellx%d' % w)
head.append('\n')
for nm, em in AUTHORS:
    head.append('\\pard\\intbl\\qc\\fi0\\sb0\\sa0\\f0\\fs22 %s\\line ' % esc(nm))
    head.append('\\fs20\\i Faculty of Computer Science and Engineering\\line '
                'Shahid Beheshti University\\line Tehran, Iran\\line \\i0 %s\\cell ' % esc(em))
head.append('\\row\n')
head.append('\\pard\\ql\\fi0\\sb120\\sa0\\f0\\fs20 \\par\n')

RTF = ('{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033\n'
       '{\\fonttbl{\\f0\\froman\\fcharset0 Times New Roman;}'
       '{\\f1\\fswiss\\fcharset0 Arial;}}\n'
       '\\paperw11906\\paperh16838\\margl1021\\margr1021\\margt1077\\margb1418\n'
       '\\sectd\\cols1\\ftnbj\\widowctrl\n'
       + ''.join(head) +
       '\\sect\\sectd\\sbknone\\cols2\\colsx397\\linex0\\widowctrl\n'
       + ''.join(B) + '}')

out = os.path.join(HERE, 'AnchorSlice_manuscript.rtf')
open(out, 'w', encoding='ascii', errors='xmlcharrefreplace').write(RTF)
print('RTF written: %.0f KB' % (os.path.getsize(out)/1024))
print('references:', len(REFS))
