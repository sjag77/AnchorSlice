#!/usr/bin/env python3
"""Build the 7-page conference version of the AnchorSlice paper as .docx.

The layout reproduces the conference template (AnchorSlice_manuscript.pages, itself
imported from the .docx that dive-llm-eval/paper/emit_docx.py generates): A4, two
columns, Times New Roman 10 pt, centred small-caps section heads, italic subsection
heads, and 8 pt tables, captions and references.

Inline markup used in the content below:
    [@key] or [@k1,k2]   citation, numbered by first appearance and linked to its reference
    **bold**  *italic*  `code`  _{subscript}

    python3 build_conference.py      # -> AnchorSlice_conference.docx
"""
import os, re, struct, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'AnchorSlice_conference.docx')
FIG1 = os.path.join(HERE, 'fig1_pipeline.png')

W_COL = 4731                 # one text column, twips
W_FULL = 9860                # full text width, twips
EMU_PER_TWIP = 635
SERIF, MONO = 'Times New Roman', 'Courier New'
LINK = '1F4FB5'              # colour of clickable citations and links

# ================================================================= REFERENCES
# key -> (entry with inline markup, (kind, target)); kind is doi | arxiv | url
REFS = {
 'szabo1997': ('N. Szabo, “Formalizing and securing relationships on public networks,” *First Monday*, vol. 2, no. 9, 1997',
               ('doi', '10.5210/fm.v2i9.548')),
 'luu2016': ('L. Luu, D.-H. Chu, H. Olickel, P. Saxena, and A. Hobor, “Making smart contracts smarter,” in *Proc. ACM SIGSAC Conf. Computer and Communications Security (CCS)*, 2016, pp. 254–269',
             ('doi', '10.1145/2976749.2978309')),
 'dasp': ('NCC Group, “Decentralized Application Security Project (DASP) Top 10,” 2018',
          ('url', 'https://dasp.co')),
 'durieux2020': ('T. Durieux, J. F. Ferreira, R. Abreu, and P. Cruz, “Empirical review of automated analysis tools on 47,587 Ethereum smart contracts,” in *Proc. ACM/IEEE Int. Conf. Software Engineering (ICSE)*, 2020, pp. 530–541',
                 ('doi', '10.1145/3377811.3380364')),
 'ghaleb2020': ('A. Ghaleb and K. Pattabiraman, “How effective are smart contract analysis tools? Evaluating smart contract static analysis tools using bug injection,” in *Proc. ACM SIGSOFT Int. Symp. Software Testing and Analysis (ISSTA)*, 2020, pp. 415–427',
                ('doi', '10.1145/3395363.3397385')),
 'feist2019': ('J. Feist, G. Grieco, and A. Groce, “Slither: A static analysis framework for smart contracts,” in *Proc. IEEE/ACM Int. Workshop on Emerging Trends in Software Engineering for Blockchain (WETSEB)*, 2019, pp. 8–15',
               ('doi', '10.1109/WETSEB.2019.00008')),
 'zhuang2020': ('Y. Zhuang, Z. Liu, P. Qian, Q. Liu, X. Wang, and Q. He, “Smart contract vulnerability detection using graph neural network,” in *Proc. Int. Joint Conf. Artificial Intelligence (IJCAI)*, 2020, pp. 3283–3290',
                ('doi', '10.24963/ijcai.2020/454')),
 'sun2024gptscan': ('Y. Sun, D. Wu, Y. Xue, H. Liu, H. Wang, Z. Xu, X. Xie, and Y. Liu, “GPTScan: Detecting logic vulnerabilities in smart contracts by combining GPT with program analysis,” in *Proc. IEEE/ACM Int. Conf. Software Engineering (ICSE)*, 2024, pp. 1–13',
                    ('doi', '10.1145/3597503.3639117')),
 'hu2023gptlens': ('S. Hu, T. Huang, F. İlhan, S. F. Tekin, and L. Liu, “Large language model-powered smart contract vulnerability detection: New perspectives,” in *Proc. IEEE Int. Conf. Trust, Privacy and Security in Intelligent Systems and Applications (TPS-ISA)*, 2023, pp. 297–306',
                   ('doi', '10.1109/TPS-ISA58951.2023.00044')),
 'ma2025iaudit': ('W. Ma, D. Wu, Y. Sun, T. Wang, S. Liu, J. Zhang, Y. Xue, and Y. Liu, “Combining fine-tuning and LLM-based agents for intuitive smart contract auditing with justifications,” in *Proc. IEEE/ACM Int. Conf. Software Engineering (ICSE)*, 2025, pp. 1–13',
                  ('arxiv', '2403.16073')),
 'he2024review': ('Z. He, Z. Li, S. Yang, A. Qiao, X. Zhang, X. Luo, and T. Chen, “Large language models for blockchain security: A systematic literature review,” 2024',
                  ('arxiv', '2403.14280')),
 'liu2024lost': ('N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, “Lost in the middle: How language models use long contexts,” *Trans. Assoc. Computational Linguistics*, vol. 12, pp. 157–173, 2024',
                 ('doi', '10.1162/tacl_a_00638')),
 'jiang2023llmlingua': ('H. Jiang, Q. Wu, C.-Y. Lin, Y. Yang, and L. Qiu, “LLMLingua: Compressing prompts for accelerated inference of large language models,” in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, 2023, pp. 13358–13376',
                        ('doi', '10.18653/v1/2023.emnlp-main.825')),
 'weiser1981': ('M. Weiser, “Program slicing,” in *Proc. Int. Conf. Software Engineering (ICSE)*, 1981, pp. 439–449',
                ('url', 'https://dl.acm.org/doi/10.5555/800078.802557')),
 'lineguard': ('P. Pakshad, S. Aghanasiri, A. Shameli-Sendi, and M. Omar, “LineGuard: An LLM-based smart contract vulnerability detection,” unpublished',
               ('url', 'https://github.com/sjag77/LineGuard')),
 'dive2026': ('S. J. Alsunaidi, H. Aljamaan, and M. Hammoudeh, “DIVE: A multi-label smart contract vulnerability dataset,” *Scientific Data*, vol. 13, art. 664, 2026; dataset',
              ('doi', '10.5281/zenodo.18519253')),
 'tsankov2018': ('P. Tsankov, A. Dan, D. Drachsler-Cohen, A. Gervais, F. Bünzli, and M. Vechev, “Securify: Practical security analysis of smart contracts,” in *Proc. ACM SIGSAC Conf. Computer and Communications Security (CCS)*, 2018, pp. 67–82',
                 ('doi', '10.1145/3243734.3243780')),
 'tikhomirov2018': ('S. Tikhomirov, E. Voskresenskaya, I. Ivanitskiy, R. Takhaviev, E. Marchenko, and Y. Alexandrov, “SmartCheck: Static analysis of Ethereum smart contracts,” in *Proc. IEEE/ACM Int. Workshop on Emerging Trends in Software Engineering for Blockchain (WETSEB)*, 2018, pp. 9–16',
                    ('doi', '10.1145/3194113.3194115')),
 'mythril': ('ConsenSys, “Mythril: Security analysis tool for EVM bytecode,” 2018',
             ('url', 'https://github.com/ConsenSys/mythril')),
 'nikolic2018': ('I. Nikolić, A. Kolluri, I. Sergey, P. Saxena, and A. Hobor, “Finding the greedy, prodigal, and suicidal contracts at scale,” in *Proc. Annual Computer Security Applications Conf. (ACSAC)*, 2018, pp. 653–663',
                 ('doi', '10.1145/3274694.3274743')),
 'so2020': ('S. So, M. Lee, J. Park, H. Lee, and H. Oh, “VeriSmart: A highly precise safety verifier for Ethereum smart contracts,” in *Proc. IEEE Symp. Security and Privacy (S&P)*, 2020, pp. 1678–1694',
            ('doi', '10.1109/SP40000.2020.00032')),
 'li2018vuldeepecker': ('Z. Li, D. Zou, S. Xu, X. Ou, H. Jin, S. Wang, Z. Deng, and Y. Zhong, “VulDeePecker: A deep learning-based system for vulnerability detection,” in *Proc. Network and Distributed System Security Symp. (NDSS)*, 2018',
                        ('doi', '10.14722/ndss.2018.23158')),
 'li2022sysevr': ('Z. Li, D. Zou, S. Xu, H. Jin, Y. Zhu, and Z. Chen, “SySeVR: A framework for using deep learning to detect software vulnerabilities,” *IEEE Trans. Dependable and Secure Computing*, vol. 19, no. 4, pp. 2244–2258, 2022',
                  ('doi', '10.1109/TDSC.2021.3051525')),
 'wei2024smartaudit': ('Z. Wei, J. Sun, Z. Zhang, X. Zhang, X. Yang, and L. Zhu, “LLM-SmartAudit: Advanced smart contract vulnerability detection,” 2024',
                       ('arxiv', '2410.09381')),
 'sun2024llm4vuln': ('Y. Sun, D. Wu, Y. Xue, H. Liu, W. Ma, L. Zhang, M. Shi, and Y. Liu, “LLM4Vuln: A unified evaluation framework for decoupling and enhancing LLMs’ vulnerability reasoning,” 2024',
                     ('arxiv', '2401.16185')),
 'jiang2024longllmlingua': ('H. Jiang, Q. Wu, X. Luo, D. Li, C.-Y. Lin, Y. Yang, and L. Qiu, “LongLLMLingua: Accelerating and enhancing LLMs in long context scenarios via prompt compression,” in *Proc. Annual Meeting of the Association for Computational Linguistics (ACL)*, 2024, pp. 1658–1677',
                            ('doi', '10.18653/v1/2024.acl-long.91')),
 'lewis2020rag': ('P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2020, pp. 9459–9474',
                  ('arxiv', '2005.11401')),
 'sridharan2007': ('M. Sridharan, S. J. Fink, and R. Bodík, “Thin slicing,” in *Proc. ACM SIGPLAN Conf. Programming Language Design and Implementation (PLDI)*, 2007, pp. 112–122',
                   ('doi', '10.1145/1250734.1250748')),
 'yashavant2022': ('C. S. Yashavant, S. Kumar, and A. Karkare, “ScrawlD: A dataset of real world Ethereum smart contracts labelled with vulnerabilities,” 2022',
                   ('arxiv', '2202.11409')),
 'zheng2024dappscan': ('Z. Zheng, J. Su, J. Chen, D. Lo, Z. Zhong, and M. Ye, “DAppSCAN: Building large-scale datasets for smart contract weaknesses in DApp projects,” *IEEE Trans. Software Engineering*, vol. 50, no. 6, pp. 1360–1373, 2024',
                       ('doi', '10.1109/TSE.2024.3383422')),
 'anchorslice_repo': ('S. Aghanasiri, S. Zaker, and A. Shameli-Sendi, “AnchorSlice: Code, data and results,” 2026',
                      ('url', 'https://github.com/sjag77/AnchorSlice')),
}

# ================================================================= OOXML PRIMITIVES
def x(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def run(t, sz=20, b=False, i=False, caps=False, font=None, color=None, sub=False):
    f = font or SERIF
    rpr = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' % (f, f, f)
    if b: rpr += '<w:b/>'
    if i: rpr += '<w:i/>'
    if caps: rpr += '<w:smallCaps/>'
    if color: rpr += '<w:color w:val="%s"/>' % color
    rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
    if sub: rpr += '<w:vertAlign w:val="subscript"/>'
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, x(t))

EXT_LINKS = []                           # (relationship id, url)
def link_external(url, runs_xml):
    rid = 'rIdLink%d' % (len(EXT_LINKS) + 1)
    EXT_LINKS.append((rid, url))
    return '<w:hyperlink r:id="%s" w:history="1">%s</w:hyperlink>' % (rid, runs_xml)

def link_internal(anchor, runs_xml):
    return '<w:hyperlink w:anchor="%s" w:history="1">%s</w:hyperlink>' % (anchor, runs_xml)

CITED = []                               # keys in order of first citation
def cite_number(key):
    if key not in REFS:
        raise KeyError('unknown reference key: ' + key)
    if key not in CITED:
        CITED.append(key)
    return CITED.index(key) + 1

TOKEN = re.compile(r'(`[^`]+`|\[@[^\]]+\]|\*\*.+?\*\*|\*[^*\s][^*]*?\*|_\{[^}]+\})')

def rich(text, sz=20, b=False, i=False):
    """Inline markup -> list of run / hyperlink XML strings."""
    out = []
    for piece in TOKEN.split(text):
        if not piece:
            continue
        if len(piece) > 1 and piece[0] == '`' and piece[-1] == '`':
            out.append(run(piece[1:-1], sz - 2, b=b, i=i, font=MONO))
        elif piece.startswith('[@'):
            for j, key in enumerate(k.strip() for k in piece[2:-1].split(',')):
                n = cite_number(key)
                if j:
                    out.append(run(', ', sz, b=b, i=i))
                out.append(run('[', sz, b=b, i=i))
                out.append(link_internal('ref_' + key, run(str(n), sz, b=b, i=i, color=LINK)))
                out.append(run(']', sz, b=b, i=i))
        elif len(piece) > 4 and piece.startswith('**') and piece.endswith('**'):
            out.extend(rich(piece[2:-2], sz, True, i))
        elif len(piece) > 2 and piece[0] == '*' and piece[-1] == '*':
            out.extend(rich(piece[1:-1], sz, b, True))
        elif piece.startswith('_{'):
            out.append(run(piece[2:-1], sz, b=b, i=i, sub=True))
        else:
            out.append(run(piece, sz, b=b, i=i))
    return out

_BOOKMARK = [0]
def para(runs, jc='both', ind=0, sb=0, sa=0, hang=0, li=0, sect=None, keep=False,
         bullet=False, bookmark=None):
    # CT_PPr child order: keepNext, keepLines, widowControl, numPr, spacing, ind, jc, sectPr
    p = '<w:pPr>'
    if keep: p += '<w:keepNext/><w:keepLines/>'
    p += '<w:widowControl/>'
    if bullet: p += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    p += '<w:spacing w:before="%d" w:after="%d" w:line="240" w:lineRule="auto"/>' % (sb, sa)
    if not bullet and (li or hang or ind):
        if hang:
            p += '<w:ind w:left="%d" w:hanging="%d"/>' % (li, hang)
        else:
            p += '<w:ind w:left="%d" w:firstLine="%d"/>' % (li, ind)
    p += '<w:jc w:val="%s"/>' % jc
    if sect: p += sect
    p += '</w:pPr>'
    content = ''.join(runs)
    if bookmark:
        _BOOKMARK[0] += 1
        content = ('<w:bookmarkStart w:id="%d" w:name="%s"/>%s<w:bookmarkEnd w:id="%d"/>'
                   % (_BOOKMARK[0], bookmark, content, _BOOKMARK[0]))
    return '<w:p>%s%s</w:p>' % (p, content)

def sectpr(cols, space=397):
    s = '<w:sectPr><w:type w:val="continuous"/>'
    s += '<w:pgSz w:w="11906" w:h="16838"/>'
    s += '<w:pgMar w:top="1077" w:right="1021" w:bottom="1418" w:left="1021" w:header="720" w:footer="720" w:gutter="0"/>'
    if cols > 1:
        s += '<w:cols w:num="%d" w:space="%d" w:equalWidth="1"/>' % (cols, space)
    else:
        s += '<w:cols w:space="%d"/>' % space
    return s + '</w:sectPr>'

RULE = '<w:%s w:val="single" w:sz="8" w:space="0" w:color="000000"/>'

def cell(content_xml, width, span=1, top=False, bottom=False):
    borders = ''
    if top or bottom:
        borders = '<w:tcBorders>%s%s</w:tcBorders>' % (RULE % 'top' if top else '', RULE % 'bottom' if bottom else '')
    gs = '<w:gridSpan w:val="%d"/>' % span if span > 1 else ''
    return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s%s<w:vAlign w:val="center"/></w:tcPr>%s</w:tc>'
            % (width, gs, borders, content_xml))

def table_open(widths):
    out = ['<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>'
           '<w:tblBorders>%s%s</w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="45" w:type="dxa"/>'
           '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="45" w:type="dxa"/></w:tblCellMar>'
           '</w:tblPr><w:tblGrid>' % (sum(widths), RULE % 'top', RULE % 'bottom')]
    out += ['<w:gridCol w:w="%d"/>' % w for w in widths]
    out.append('</w:tblGrid>')
    return out

def data_table(rows, widths, aligns, head_rows=1, sz=16, rule_before=()):
    """rows: list of cell-markup lists, or ('span', markup) for a full-width subheading row."""
    out = table_open(widths)
    for ri, r in enumerate(rows):
        head = ri < head_rows
        out.append('<w:tr><w:trPr><w:cantSplit/>%s</w:trPr>' % ('<w:tblHeader/>' if head else ''))
        if isinstance(r, tuple) and r[0] == 'span':
            out.append(cell(para(rich(r[1], sz, i=True), jc='left', sb=24, sa=0), sum(widths),
                            span=len(widths), top=ri in rule_before))
        else:
            for ci, c in enumerate(r):
                out.append(cell(para(rich(c, sz, b=head), jc=aligns[ci], sb=6, sa=6), widths[ci],
                                top=ri in rule_before, bottom=head and ri == head_rows - 1))
        out.append('</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)

def algorithm_table(title, io_lines, lines, sz=15):
    """Ruled algorithm box: title row, input/output rows, then numbered pseudocode lines."""
    widths = [300, W_COL - 300]
    out = table_open(widths)
    out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
    out.append(cell(para(rich(title, 16), jc='left', sb=20, sa=20), sum(widths), span=2, bottom=True))
    out.append('</w:tr>')
    for label, text in io_lines:
        out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        out.append(cell(para([run(label + ' ', sz, b=True)] + rich(text, sz), jc='left', sb=4, sa=4),
                        sum(widths), span=2))
        out.append('</w:tr>')
    for n, (level, text) in enumerate(lines, 1):
        out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        out.append(cell(para([run('%d:' % n, sz - 1)], jc='right'), widths[0]))
        out.append(cell(para(rich(text, sz), jc='left', li=60 + 220 * level), widths[1]))
        out.append('</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)

def listing_table(lines, sz=12):
    """Framed monospace listing in one column."""
    out = table_open([W_COL])
    out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
               '<w:tcBorders>%s%s%s%s</w:tcBorders></w:tcPr>'
               % (W_COL, RULE % 'top', RULE % 'left', RULE % 'bottom', RULE % 'right'))
    for ln in lines:
        out.append(para([run(ln, sz, font=MONO)], jc='left', li=40))
    out.append('</w:tc></w:tr></w:tbl>')
    return ''.join(out)

_IMG = []
def image_xml(path, goal_tw):
    d = open(path, 'rb').read()
    w, h = struct.unpack('>II', d[16:24])
    cx = goal_tw * EMU_PER_TWIP
    cy = int(cx * h / w)
    n = len(_IMG) + 1
    rid = 'rIdImg%d' % n
    _IMG.append((rid, path, n))
    return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            '<wp:extent cx="%d" cy="%d"/><wp:docPr id="%d" name="Figure %d"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="%d" name="Figure %d"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
            % (cx, cy, 100 + n, n, 100 + n, n, rid, cx, cy))

# ================================================================= DOCUMENT BUILDER
BODY = []
_H1, _H2 = [0], [0]
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

def H1(title):
    _H1[0] += 1; _H2[0] = 0
    BODY.append(para([run('%s.  %s' % (ROMAN[_H1[0] - 1], title), 20, caps=True)],
                     jc='center', sb=160, sa=80, keep=True))

def H2(title):
    _H2[0] += 1
    BODY.append(para([run('%s. %s' % ('ABCDEFGHIJ'[_H2[0] - 1], title), 20, i=True)],
                     jc='left', sb=100, sa=60, keep=True))

def P(text, indent=True):
    BODY.append(para(rich(text, 20), ind=200 if indent else 0))

def BULLETS(items):
    for it in items:
        BODY.append(para(rich(it, 20), bullet=True, sa=20))

def WIDE_START():
    """End the running two-column section so the following floats span the page."""
    last = BODY[-1]
    if last.startswith('<w:p>') and '</w:pPr>' in last and '<w:sectPr>' not in last:
        BODY[-1] = last.replace('</w:pPr>', sectpr(2) + '</w:pPr>', 1)
    else:
        BODY.append(para([], sect=sectpr(2)))

def WIDE_END():
    BODY.append(para([run('', 4)], sa=40, sect=sectpr(1)))

def TABLE(caption, rows, widths, aligns, note=None, rule_before=()):
    BODY.append(para([run(caption, 16, caps=True)], jc='center', sb=120, sa=60, keep=True))
    BODY.append(data_table(rows, widths, aligns, rule_before=rule_before))
    if note:
        BODY.append(para(rich(note, 14), jc='both', sb=30, sa=100))
    else:
        BODY.append(para([run('', 4)], sa=60))

def ALGORITHM(title, io_lines, lines):
    BODY.append(para([run('', 4)], sb=40, keep=True))
    BODY.append(algorithm_table(title, io_lines, lines))
    BODY.append(para([run('', 4)], sa=60))

def FIGURE(path, caption):
    BODY.append(image_xml(path, 9600))
    BODY.append(para(rich(caption, 16), jc='both', sb=60, sa=100))

def LISTING(lines, caption):
    BODY.append(para([run('', 4)], sb=40, keep=True))
    BODY.append(listing_table(lines))
    BODY.append(para(rich(caption, 16), jc='both', sb=60, sa=100))

def author_table(authors):
    cells = []
    for name, email in authors:
        c = ['<w:tc><w:tcPr><w:tcW w:w="3286" w:type="dxa"/></w:tcPr>']
        c.append(para([run(name, 22)], jc='center'))
        for ln in ('Faculty of Computer Science and Engineering', 'Shahid Beheshti University', 'Tehran, Iran'):
            c.append(para([run(ln, 20, i=True)], jc='center'))
        c.append(para([run(email, 20)], jc='center'))
        c.append('</w:tc>')
        cells.append(''.join(c))
    return ('<w:tbl><w:tblPr><w:tblW w:w="9858" w:type="dxa"/><w:jc w:val="center"/>'
            '<w:tblCellMar><w:left w:w="60" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar>'
            '</w:tblPr><w:tblGrid><w:gridCol w:w="3286"/><w:gridCol w:w="3286"/><w:gridCol w:w="3286"/></w:tblGrid>'
            '<w:tr>' + ''.join(cells) + '</w:tr></w:tbl>')

# ================================================================= CONTENT
TITLE = ('AnchorSlice: Anchor-Guided Static Slicing for Token-Efficient Smart Contract '
         'Vulnerability Detection')
AUTHORS = [('Sajad Aghanasiri', 's.aghanasiri@sbu.ac.ir'),
           ('Sina Zaker', 's.zaker@sbu.ac.ir'),
           ('Alireza Shameli-Sendi', 'a_shameli@sbu.ac.ir')]

ABSTRACT = (
    "Automated vulnerability detection is essential for smart contracts, which cannot be patched "
    "once deployed. Detectors that reason over source code are increasingly capable, but their cost, "
    "latency and context capacity are bounded by the number of tokens they read, and most of a deployed "
    "contract is comments, library code and boilerplate that cannot host a vulnerability. This paper "
    "presents AnchorSlice, a static, model-free method that makes smart contract vulnerability detection "
    "token-efficient. From one anchor set per DASP category it builds two components: a slicer that reduces "
    "each contract, before it reaches the detector, to the fragments able to host each category, and "
    "anchor-derived decision rules that tell the detector what each category means in this corpus. AnchorSlice is purely lexical: anchor expressions and "
    "brace matching decide what survives, overlapping regions are merged once and tagged with the "
    "categories they may host, and library code is collapsed under a rescue rule that preserves "
    "evidence. On 200 contracts from the DIVE benchmark it retains 56.5% of source characters, preserves "
    "evidence for all 463 labelled category instances and needs 7.6 ms per contract. We compare the way a "
    "source-level detector is used in practice, submitting the complete contract with a short instruction, "
    "against the same detector driven by AnchorSlice. Token consumption "
    "falls by 55.2%, cost by 63.7% and runtime by 59.7%, while F1-score rises from 0.342 to 0.693 and "
    "agreement from 0.642 to 0.801; missed vulnerabilities fall from 314 to 104 and false positives from "
    "259 to 214 at the same time. The slicer accounts for the token saving and the decision rules for the "
    "detection gain, so one static artefact makes the same detector both cheaper and better.")
KEYWORDS = ("smart contract vulnerability detection, token efficiency, static slicing, input reduction, "
            "blockchain security, DASP")

SLICE_EXCERPT = [
    "// SLICED CONTRACT 19288: 128 src lines -> 61 kept (48%), 5 candidate blocks.",
    "// Each block lists the DASP categories whose static anchors fired inside it.",
    "// Omitted code matched no anchor for any category.",
    "// [standard SafeMath omitted - unmodified reference implementation]",
    "// --- DECLARATIONS ---",
    "pragma solidity ^0.4.18;",
    "[...]",
    "// --- BLOCK 2 | src L16-21 | candidates: Access Control, DoS",
    "    modifier onlyCLevel() {",
    "    require(",
    "      msg.sender == ceoAddress",
    "    );",
    "    _;",
    "    }",
    "// --- BLOCK 3 | src L23-26 | candidates: Access Control, Front Running",
    "    function AdPotato() public{",
    "        ceoAddress=msg.sender;",
    "        initialize(0x58AFF91f5b48245Bd83deeB2C7d31875f68b3f0D);",
    "    }",
    "[...]",
]

def build_content():
    # ---------------------------------------------------------------- I
    H1('Introduction')
    P("Smart contracts cannot be patched once deployed, so their vulnerabilities must be found before "
      "deployment, and detectors that read contract source code have become one of the most capable ways "
      "to find them. Their cost, however, grows with the length of what they read, while most of a deployed "
      "contract cannot host any vulnerability. This section motivates token-efficient smart contract "
      "vulnerability detection. It first explains why contract defects are costly and why existing analysers "
      "leave detection open, then shows how input length limits source-level detectors, and finally "
      "introduces AnchorSlice, its contributions and the research questions that structure the evaluation.",
      indent=False)
    P("Smart contracts execute agreements without a trusted intermediary [@szabo1997] and, on Ethereum, hold "
      "and move assets directly. Their code is public and immutable, so any defect stays reachable by an "
      "adversary; the 2016 DAO reentrancy attack, which drained about sixty million dollars, motivated the "
      "first automated analysers [@luu2016], and recurring fault patterns were later organised into the "
      "Decentralized Application Security Project (DASP) Top 10 [@dasp]. Analysers still leave the problem "
      "open. Nine widely used tools run over 47,587 contracts found only a minority of the annotated faults "
      "while flagging 97% of the corpus [@durieux2020], and injected faults of well-known shapes routinely "
      "escape detection [@ghaleb2020]. Many real defects are semantic, which fixed rules such as those of "
      "Slither [@feist2019] cannot capture, and learning-based detectors were introduced partly to close "
      "this gap [@zhuang2020].")
    P("Detectors that reason over source code with pre-trained language models moved the field further. "
      "Pipelines that pair model reasoning with static confirmation [@sun2024gptscan], separate generation "
      "from criticism [@hu2023gptlens], or combine fine-tuned detectors with cooperating agents "
      "[@ma2025iaudit] report detection quality beyond pattern-based tools, and the literature is growing "
      "quickly [@he2024review]. In these systems the model is one component of the detector, and all of them "
      "consume the contract source. That dependence has a cost that scales with input length: a source-level "
      "detector is billed per token, bounded by a context window, and less reliable when evidence is buried "
      "inside a long input [@liu2024lost]. A fixed-supply ERC-20 token is several hundred lines of library "
      "boilerplate around perhaps thirty lines that could hold a flaw, yet the whole file is submitted. "
      "Generic prompt compression drops low-information tokens with a small model [@jiang2023llmlingua], but "
      "it spends model capacity itself and cannot guarantee that security-relevant code survives.")
    P("We exploit the fact that vulnerability classes have lexical footprints: reentrancy requires an "
      "external call, bad randomness a block-derived value, and an arithmetic fault an operator. Code with "
      "none of these cannot host the corresponding defect, and deciding that requires no model. AnchorSlice "
      "is a purely static slicing stage that keeps, for each DASP category, only the regions whose tokens "
      "make the category possible, and hands the detector a compact annotated slice. It borrows the "
      "intuition of program slicing [@weiser1981] without dependence analysis, and extends the candidate "
      "pruning of our LineGuard framework [@lineguard], which serves one category per query, to all eight "
      "categories in a single pass. This paper contributes (i) AnchorSlice, a detector-agnostic lexical "
      "slicer with a DASP anchor set, a visibility gate, a tag-preserving merge and an evidence-preserving "
      "library collapse; (ii) its validation on the DIVE benchmark [@dive2026], showing full evidence "
      "retention across 200 contracts at 56.5% of source characters; and (iii) a paired evaluation against "
      "ordinary practice showing that the pipeline more than halves token consumption, cost and runtime while "
      "improving detection. The evaluation answers three research questions:")
    BULLETS([
        "**RQ1 (Evidence retention):** To what extent can a purely lexical, taxonomy-anchored slice reduce a "
        "contract's source while preserving the evidence for every labelled vulnerability category?",
        "**RQ2 (Token efficiency):** How much do the token consumption, runtime and cost of vulnerability "
        "detection fall when the detector receives the slice instead of the complete contract?",
        "**RQ3 (Detection effectiveness):** How does slicing affect vulnerability detection effectiveness, "
        "overall and for each DASP category?",
    ])
    P("Section II reviews related work, Section III presents AnchorSlice, Section IV reports the evaluation "
      "and answers the research questions, Section V discusses limitations, and Section VI concludes.",
      indent=False)

    # ---------------------------------------------------------------- II
    H1('Background and Related Work')
    P("Token-efficient detection lies where three bodies of work meet. This section first reviews smart "
      "contract vulnerability analysers and detectors with attention to the input they consume, then input "
      "reduction and program slicing, and finally the labelled benchmarks used for evaluation and the "
      "position of AnchorSlice among these works.", indent=False)
    H2('Vulnerability Analysers and Detectors')
    P("Rule-based tools established automated contract analysis. Oyente applied symbolic execution to EVM "
      "bytecode [@luu2016], Securify matched compliance and violation patterns over dependence graphs "
      "[@tsankov2018], SmartCheck queried an XML representation of Solidity [@tikhomirov2018], Mythril "
      "combined symbolic execution with taint analysis [@mythril], MAIAN searched for traces that leak or "
      "lock funds [@nikolic2018], VeriSmart verified arithmetic safety through transaction invariants "
      "[@so2020], and Slither runs detectors over an SSA-based intermediate form [@feist2019]. Because these "
      "tools execute analyses rather than read tokens, input length is not their bottleneck. Learning-based "
      "detectors changed the representation: VulDeePecker learned from code gadgets sliced around API calls "
      "[@li2018vuldeepecker], SySeVR sliced programs over dependence graphs [@li2022sysevr], and Zhuang et al. "
      "applied graph neural networks to normalised contract graphs [@zhuang2020]. Their reductions serve a "
      "trained representation rather than a vulnerability taxonomy, and they must be retrained when the "
      "representation changes.", indent=False)
    P("Source-level detectors built on language models read the contract itself: GPTScan validates "
      "model-nominated candidates with static modules [@sun2024gptscan], GPTLens pairs auditor and critic roles "
      "[@hu2023gptlens], LLM-SmartAudit coordinates multiple agents [@wei2024smartaudit], LLM4Vuln separates "
      "knowledge, tool use and reasoning [@sun2024llm4vuln], and iAudit combines fine-tuned detectors with "
      "ranking and critic agents [@ma2025iaudit]. All of them receive the whole contract, and context length is "
      "a recurring constraint in this line of work [@he2024review]. LineGuard [@lineguard] already narrows the "
      "input by ranking candidate lines with category-specific regular expressions and passing the top-ranked "
      "lines with a fixed context window, but it does so for one category given in advance and without "
      "isolating the effect of pruning on evidence or token cost.")
    H2('Input Reduction and Program Slicing')
    P("Generic methods reduce long inputs statistically. LLMLingua drops low-information tokens with a small "
      "language model [@jiang2023llmlingua], LongLLMLingua adds question-aware compression "
      "[@jiang2024longllmlingua], and retrieval-augmented generation fetches only relevant passages "
      "[@lewis2020rag]; none of them can guarantee that a security-critical statement survives. Program "
      "slicing offers that guarantee by computing the statements that affect a criterion [@weiser1981], and "
      "thin slicing keeps only value-producing statements [@sridharan2007], but both need a compilable program "
      "and a dependence graph, a strong requirement for deployed contracts spanning many compiler versions. "
      "AnchorSlice sits between these positions: coarser than dependence-based slicing, model-free unlike "
      "prompt compression, and guided by the vulnerability taxonomy itself.", indent=False)
    H2('Benchmarks and Positioning')
    P("ScrawlD labels real contracts by majority vote over five analysers [@yashavant2022], and DAppSCAN "
      "derives weakness datasets from 1,199 audit reports [@zheng2024dappscan]. We use DIVE [@dive2026], which "
      "labels 22,330 contracts against DASP categories 1–8 by aggregating MAIAN, Mythril, Semgrep, Slither, "
      "Solhint and VeriSmart through power-based voting with post-hoc validation of positive findings. Its "
      "labels are assigned per contract, which determines how evidence retention can be validated. To our "
      "knowledge, AnchorSlice is the first input "
      "reduction stage for vulnerability detection that is at once model-free, guided by a full vulnerability "
      "taxonomy, and validated for evidence retention on a labelled smart contract benchmark.", indent=False)

    # ---------------------------------------------------------------- III
    H1('AnchorSlice')
    P("AnchorSlice is built from one artefact, the anchor set of each DASP category, and turns it into two "
      "components a detector uses together: a static slicer that keeps, for every category, the regions able "
      "to host it, so the detector reads far fewer tokens without losing evidence, and anchor-derived "
      "decision rules that state which shapes count as an instance of each category in this corpus. The "
      "slicer governs how much the detector reads and therefore what a query costs; the rules govern how it "
      "judges what it reads and therefore what the query is worth; neither costs a model call. Fig. 1 places the slicer in the detection pipeline, Table I lists its anchors, and "
      "Algorithm 1 gives the procedure. This section first states the design principles, then describes the "
      "lexical anchors and the visibility gate, the extraction and merging of windows together with library "
      "collapse, and finally the rendering of the slice for the detector, illustrated in Fig. 2.", indent=False)

    WIDE_START()
    FIGURE(FIG1, "**Fig. 1.**  AnchorSlice and the practice it replaces. Conventionally the whole contract "
                 "is handed to the detector with a one-line list of the categories. AnchorSlice derives two "
                 "static components from one anchor set per DASP category: a slicer, which emits a tagged "
                 "slice of 56.5% of the source characters while retaining all 463 labelled category "
                 "instances, and decision rules, which state what each category means in this corpus. "
                 "Detector and output schema are identical in both arms; figures beneath each lane are per "
                 "contract.")
    S = ' · '
    TABLE('Table I.  Anchor Specification for the Eight DASP Categories', [
        ['Category', 'Anchor expressions', 'Gate', 'Retained'],
        ['Reentrancy', '`EXT`', 'view/pure', '98/98'],
        ['Access Control', S.join('`%s`' % a for a in ['modifier', 'only\\w+', '(_)owner =', 'tx.origin',
            'selfdestruct', 'suicide', 'delegatecall', 'require(msg.sender', 'renounce', 'transferOwnership',
            'authoriz', 'admin', 'MUTFN']), 'view/pure', '144/144'],
        ['Arithmetic', S.join('`%s`' % a for a in ['[+ - * / %]=', '++', '--', 'x [+ * / %] y', 'x - y', '**',
            '<<', '>>', 'unchecked']), '–', '84/84'],
        ['Unchecked Return Values', '`EXT`', 'view/pure', '38/38'],
        ['DoS', S.join('`%s`' % a for a in ['for(', 'while(', '.push(', '.length', 'require(', 'revert',
            'assert(', 'EXT']), 'view/pure', '26/26'],
        ['Bad Randomness', S.join('`%s`' % a for a in ['blockhash',
            'block.{difficulty, coinbase, gaslimit, number, timestamp, prevrandao}', 'now', 'keccak256',
            'sha3(', 'sha256', 'random', 'nonce', 'seed']), '–', '16/16'],
        ['Front Running', S.join('`%s`' % a for a in ['approve(', 'allowance', 'msg.value', 'tx.gasprice',
            'price', 'bid', 'swap*(', 'slippage', 'amountOutMin', 'deadline', 'reserve', 'MUTFN']),
         'view/pure', '15/15'],
        ['Time manipulation', S.join('`%s`' % a for a in ['now', 'block.timestamp', 'block.number',
            'N {days, hours, minutes, seconds, weeks}', 'deadline', 'startTime', 'endTime', 'cooldown',
            'lastClaim', 'timeout']), '–', '42/42'],
        ['**All categories**', '', '', '**463/463**'],
    ], [1560, 6650, 800, 850], ['left', 'left', 'center', 'right'], rule_before=(9,),
      note="`EXT` matches low-level calls (`.call`, `.call.value`, `.send`, `.transfer`, `delegatecall`, "
           "`staticcall`), calls through an interface cast, `transferFrom`/`_transfer`, swap and add-liquidity "
           "calls, `payable(` conversions, inline `assembly`, and calls on any receiver that is not a language "
           "builtin. `MUTFN` matches any public or external function not declared `view` or `pure`. The gate "
           "column names the only semantic restriction retained after ablation. Retained counts the "
           "label-positive contracts that keep at least one block tagged with the category.")
    WIDE_END()

    H2('Design Principles')
    P("Three requirements shaped the design. The slicer must be fully static, deciding everything with "
      "regular expressions and brace counting, because a slicer that consulted a model would spend the "
      "budget it is meant to save. It must emit each region at most once: eight independent category passes "
      "would overlap heavily, so AnchorSlice makes a single pass and attaches a set of candidate categories to "
      "each region (Algorithm 1, lines 4–13). Finally, it must be detector-agnostic, emitting ordinary "
      "Solidity text with comment headers that any source-level detector can read.", indent=False)
    algorithm_1 = lambda: ALGORITHM('**Algorithm 1.**  AnchorSlice', [
        ('Input:', 'source *S*; categories *C* with anchors *A*_{c}; gated set *V*; cap *κ*; padding *π*'),
        ('Output:', 'annotated slice *Σ*'),
    ], [
        (0, '*L* ← StripComments(*S*)'),
        (0, '*K* ← lines of top-level library units in *L*   ▷ collapsed'),
        (0, '*W* ← ∅'),
        (0, '**for each** function (*f*_{s}, *f*_{e}, *sig*) in *L* with *f*_{s} ∉ *K* **do**'),
        (1, '*G* ← *V* **if** *sig* is view or pure **else** ∅'),
        (1, '**for** *k* = *f*_{s} **to** *f*_{e} **do**'),
        (2, '*T* ← {*c* ∈ *C* \\ *G* : *A*_{c} matches *L*[*k*]}'),
        (2, '**if** *T* ≠ ∅ **then**'),
        (3, '(*a*, *b*) ← InnermostBlock(*L*, *f*, *k*, *κ*, *π*)'),
        (3, '*W* ← *W* ∪ {(*a*, *b*, *T*)}'),
        (2, '**end if**'),
        (1, '**end for**'),
        (0, '**end for**'),
        (0, '*B* ← MergeAdjacent(*W*)   ▷ union of tags'),
        (0, '**for each** *c* ∈ *C* tagged in no block of *B* **do**'),
        (1, '**if** some *k* ∈ *K* has *A*_{c} matching *L*[*k*] **then**'),
        (2, '*B* ← *B* ∪ {(*k*−1, *k*+1, {*c*})}   ▷ rescue'),
        (1, '**end if**'),
        (0, '**end for**'),
        (0, '*Σ* ← Render(stubs(*K*), declarations(*L*), *B*)'),
        (0, '**if** |*Σ*| ≥ |*L*| **then** *Σ* ← *L*   ▷ small contract: send whole'),
        (0, '**return** *Σ*'),
    ])
    H2('Lexical Anchors and the Visibility Gate')
    P("Each category owns anchor expressions, listed in Table I, and a line that matches one marks its "
      "enclosing region as a candidate for that category (line 7). Two macros carry most of the weight. "
      "`EXT` matches external and cross-contract calls, including low-level `call`, `send`, `transfer`, "
      "`delegatecall` and `staticcall` forms and calls through interface casts. `MUTFN` matches every public "
      "or external function not declared `view` or `pure`, the only static way to surface access-control "
      "faults that consist of a missing modifier.", indent=False)
    P("We evaluated five semantic gates for suppressing safe regions and retained one. Suppressing arithmetic "
      "candidates under Solidity 0.8 cut arithmetic retention from 1.00 to 0.43, requiring a state write "
      "before a reentrancy candidate cut it from 0.91 to 0.36, and treating a call wrapped in `require` as "
      "checked cut unchecked-return retention from 0.60 to 0.20, because the benchmark labels such cases "
      "positive. Only the visibility gate survived: excluding `view` and `pure` bodies from the five "
      "state-dependent categories cost no retention (line 5). The rejected gates were sound Solidity reasoning "
      "but disagreed with the benchmark's annotation policy, a reminder that a slicer tuned to a dataset "
      "inherits its conventions.")
    algorithm_1()          # placed after III-B text so it never directly follows the wide block
    H2('Window Extraction, Merging and Library Collapse')
    P("An anchored line expands to its innermost enclosing brace block, capped at 10 lines, beyond which the "
      "window falls back to the anchor with two lines of context on each side (line 9); the enclosing "
      "signature is kept so that visibility and modifiers stay visible. Overlapping or adjacent windows merge "
      "into one block whose tags are the union of theirs (line 14), so a region relevant to several categories "
      "is emitted once; the sample averages 16.6 blocks per contract. Standard library constructs such as "
      "SafeMath, Address, Context, Ownable, ERC20 and common exchange interfaces are recognised by name and "
      "replaced with one-line stubs (line 2). Collapse alone lowered access-control retention to 0.95 and DoS "
      "retention to 0.86, because some contracts kept their only anchor inside library code, so a rescue rule "
      "emits a three-line window at such an anchor whenever a category would otherwise have no block "
      "(lines 15–19), restoring full retention for about two percentage points of size.", indent=False)
    H2('Slice Rendering')
    P("The slice lists library stubs and contract-level declarations, then the blocks in source order, each "
      "with a header giving its original line range and candidate categories so that a finding can be traced "
      "back (line 20). Fig. 2 shows an excerpt for a contract from the sample: `SafeMath` is reduced to a stub, "
      "block 2 is a modifier tagged for access control because it constrains `msg.sender` and for DoS because "
      "it contains `require`, and block 3 is a public function tagged by `MUTFN`. A short preamble tells the "
      "detector that tags are lexical hints rather than findings and that most tagged blocks are not "
      "vulnerable. When block headers would cost more than the removed lines save, the contract is sent whole "
      "with comments stripped (line 21), which happened for 43 of the 200 contracts.", indent=False)
    LISTING(SLICE_EXCERPT, "**Fig. 2.**  Excerpt of the AnchorSlice output for DIVE contract 19288. Lines "
                           "marked [...] are elided for space; all other lines are reproduced verbatim.")

    # ---------------------------------------------------------------- IV
    H1('Experimental Evaluation')
    P("This section evaluates whether AnchorSlice makes vulnerability detection more token-efficient without "
      "degrading it. The detector is held fixed and only its input changes, comparing complete contracts "
      "(Arm A) with AnchorSlice output (Arm B) on the same contracts. It first describes the setup, dataset "
      "and protocol, then reports evidence retention, resource consumption, detection effectiveness and "
      "per-category behaviour, and finally answers the research questions.", indent=False)
    H2('Setup and Dataset')
    P("AnchorSlice and the evaluation harness use only the Python standard library, and the code, samples, "
      "raw results and logs are available in the project repository [@anchorslice_repo]. Slicer runtime was "
      "measured on an Intel Core i9-9880H with Python 3.12.3. In both arms the detector is Claude Opus 5 at "
      "high reasoning effort, accessed through the Claude Code command-line interface in print mode with all "
      "tools disabled and no session persistence, so it sees only the prompt. A JSON schema forces eight "
      "binary labels with confidences and short reasons, and the interface exposes no sampling parameters. "
      "Table II lists every parameter, all held fixed across both arms.", indent=False)
    P("Across all 22,330 DIVE contracts, prevalence ranges from 74.9% for access control to 2.7% for front "
      "running, so we drew 200 contracts with seeded random sampling, repaired so that every category carries "
      "enough positives and negatives to be measurable, excluding files below 1,200 or above 30,000 bytes. "
      "The sample holds 2,311,110 characters, none truncated, and 463 positives among 1,600 label cells "
      "(28.9%). Common categories track the corpus closely, while bad randomness (8.0% against 2.8%) and "
      "front running (7.5% against 2.7%) are deliberately over-sampled so that they can be scored at all. "
      "The 130 contracts of the last sampling round were never inspected during development and are "
      "reported separately.")
    TABLE('Table II.  Experimental Configuration', [
        ['Parameter', 'Value', 'Description'],
        ('span', 'Slicer'),
        ['Window cap', '10 lines', 'Largest block kept whole'],
        ['Padding', '±2 lines', 'Context beyond the cap'],
        ['Gated categories', '5', 'Off in view/pure bodies'],
        ('span', 'Sampling'),
        ['Sample size', '200', 'Stratified, three rounds'],
        ['Category floor', '5', 'Min. positives/negatives'],
        ['Size filter', '1.2–30 kB', 'Excludes stubs, bounds cost'],
        ('span', 'Detector'),
        ['Model', 'Claude Opus 5', 'High reasoning effort'],
        ['Access', 'Claude Code CLI', 'Print mode, no tools'],
        ['Output', 'JSON schema', 'Labels, confidences, reasons'],
        ['Calls', '1 per contract', 'Sequential, 900 s timeout'],
    ], [1250, 1450, 2031], ['left', 'left', 'left'])
    H2('Evaluation Protocol')
    P("Arm A is ordinary practice: the complete contract with a short instruction naming the eight "
      "categories in one line each. Arm B is AnchorSlice with both components: the slice with its preamble, "
      "and the anchor-derived decision rules, each category carrying a code example, a decision rule and its "
      "corpus base rate. Detector, effort, schema and contracts are identical, with one call each. Against "
      "the DIVE labels we report label agreement, exact match, micro-averaged precision, recall and F1-score, "
      "and Cohen's kappa, with McNemar's exact test on the 1,600 paired cells, together with total tokens, "
      "wall-clock time and cost. Evidence retention, measured without the detector, is the share of "
      "label-positive contracts that keep at least one block tagged with the category.", indent=False)
    H2('Evidence Retention')
    P("AnchorSlice reduced the sample from 2,311,110 to 1,305,860 characters (56.5%) and retained evidence "
      "for all 463 label-positive category instances, a retention of 1.00 in every category (Table I). Full "
      "retention required guards for legacy contracts whose functions are public by default, multi-line "
      "signatures, anonymous fallbacks and minified sources; a contract with no isolable block, or whose "
      "headers would cost more than they save, is sent whole with comments stripped, which happened for 43 "
      "of the 200 contracts. Slicing costs 7.6 ms per contract on average and 17.5 ms at most, negligible "
      "beside a detector call of tens of seconds.", indent=False)
    H2('Token Consumption, Runtime and Cost')
    P("As Table III shows, the pipeline cut total tokens from 2,092,914 to 937,754 (−55.2%), from 10,465 to "
      "4,689 per contract, wall-clock time from 4,151 to 1,673 s (−59.7%) and cost from $17.75 to $6.45 "
      "(−63.7%), which is $0.032 and 8.4 s per contract against $0.089 and 20.8 s. The contract text read "
      "fell by 69.1% and output tokens by 55.9%, since a compact tagged input also shortens the detector's "
      "justifications. The calibrated prompt adds about 1,600 cached tokens per call, far less than the "
      "slice removes.", indent=False)
    TABLE('Table III.  Resource Use and Detection Effectiveness', [
        ['Measure', 'Arm A', 'Arm B', 'Change'],
        ('span', 'Resources (200 contracts)'),
        ['Total tokens', '2,092,914', '937,754', '−55.2%'],
        ['Tokens per contract', '10,465', '4,689', '−55.2%'],
        ['Output tokens', '254,939', '112,469', '−55.9%'],
        ['Contract text cached', '1,100,024', '339,432', '−69.1%'],
        ['Wall clock (s)', '4,151', '1,673', '−59.7%'],
        ['Cost (USD)', '17.75', '6.45', '−63.7%'],
        ('span', 'Detection effectiveness (1,600 label cells)'),
        ['Precision', '0.365', '0.627', '+0.262'],
        ['Recall', '0.322', '0.775', '+0.453'],
        ['F1-score', '0.342', '0.693', '+0.351'],
        ["Cohen's kappa", '0.097', '0.549', '+0.452'],
        ['Label agreement', '0.642', '0.801', '+0.159'],
        ['Exact match (8/8)', '5/200', '28/200', '+23'],
        ['True positives', '149', '359', '+210'],
        ['False positives', '259', '214', '−45'],
        ['False negatives', '314', '104', '−210'],
    ], [1831, 950, 950, 1000], ['left', 'right', 'right', 'right'])
    H2('Detection Effectiveness')
    P("Detection improved on every aggregate measure (Table III). Recall rose from 0.322 to 0.775 and precision "
      "from 0.365 to 0.627, so the additional detections did not come from over-reporting; F1-score rose from "
      "0.342 to 0.693 and Cohen's kappa from 0.097 to 0.549. Missed vulnerabilities fell from 314 to 104 while "
      "false positives fell from 259 to 214, so both error types improved together, and 28 contracts were "
      "labelled correctly in all eight categories against 5 before; at contract level 142 improved, 31 were "
      "unchanged and 27 regressed. Over the 1,600 paired cells, 170 were correct only in Arm A and 425 only in "
      "Arm B (McNemar exact p about 3.7 × 10⁻²⁶). On the 130 contracts never inspected during development the "
      "result is unchanged (F1-score 0.689), and with the prompt held fixed the slice alone left detection "
      "unchanged (p = 1.00) while still cutting tokens.", indent=False)
    H2('Per-Category Behaviour')
    P("Table IV breaks agreement down by category: six improve and two regress. Reentrancy rises from 0.19 to "
      "0.82 as misses fall from 88 to 2, and access control from 0.41 to 0.83 with misses falling from 102 to "
      "9; asked to report only exploitable faults, the baseline marked 10 of 98 reentrancy and 42 of 144 "
      "access-control contracts, while the `MUTFN` anchor marks exactly the entry points where a missing "
      "modifier would live. Unchecked return values (0.46 to 0.74) and DoS (0.17 to 0.47) improve by shedding "
      "false positives. Time manipulation falls from 0.67 to 0.58, recovering misses at the cost of false "
      "positives, and front running falls to zero: the calibrated rule cuts 132 false positives to 14 but "
      "recovers none of its 15 positives (Section V).", indent=False)
    TABLE('Table IV.  Label Agreement per DASP Category', [
        ['Category', 'DIVE+', 'F1 A', 'F1 B', 'FP A', 'FP B', 'FN A', 'FN B'],
        ['Reentrancy', '98', '0.19', '0.82', '0', '39', '88', '2'],
        ['Access control', '144', '0.41', '0.83', '17', '46', '102', '9'],
        ['Arithmetic', '84', '0.44', '0.52', '25', '48', '53', '38'],
        ['Unchecked return', '38', '0.46', '0.74', '23', '5', '20', '13'],
        ['DoS', '26', '0.17', '0.47', '50', '10', '19', '15'],
        ['Bad randomness', '16', '0.58', '0.62', '1', '2', '9', '8'],
        ['Front running', '15', '0.09', '0.00', '132', '14', '8', '15'],
        ['Time manipulation', '42', '0.67', '0.58', '11', '50', '15', '4'],
        ['**All**', '**463**', '**0.342**', '**0.693**', '**259**', '**214**', '**314**', '**104**'],
    ], [1251, 520, 520, 520, 480, 480, 480, 480], ['left'] + ['right'] * 7, rule_before=(9,),
      note="DIVE+: reference positives; A: complete source with the simple prompt; B: AnchorSlice with the "
           "calibrated prompt; FP/FN: false positives and false negatives.")
    H2('Discussion')
    P("Removing about 40% of each contract did not degrade detection and improved it on aggregate. Comments, "
      "licence headers and unmodified libraries carry no evidence a security judgement needs, and a shorter "
      "input raises the density of relevant code, consistent with the finding that evidence buried in long "
      "inputs is used less reliably [@liu2024lost]. Since comment removal and library collapse deliver nearly "
      "all of the compression, the main value of anchoring is localisation: the tags show the detector where "
      "each category could live, and an anchor helps in proportion to its selectivity. We now revisit the "
      "research questions.", indent=False)
    P("**RQ1 — Evidence retention.** The slicer kept 56.5% of the characters, 16.6 blocks per contract, and a "
      "tagged block for every one of the 463 label-positive category instances, a retention of 1.00 in all "
      "eight categories; the rescue rule and guards for legacy visibility, multi-line signatures, anonymous "
      "fallbacks and minified sources were needed to reach it.", indent=False)
    P("**To best answer RQ1:** a purely lexical, taxonomy-anchored slice removed about two fifths of the source "
      "while retaining evidence for every labelled category instance at 7.6 ms per contract. Because retention "
      "is measured per contract, this shows that no labelled evidence is discarded, not that the specific "
      "vulnerable statements survive.", indent=False)
    P("**RQ2 — Token efficiency.** Total tokens fell by 55.2%, the contract text read by 69.1% and output by "
      "55.9%, while runtime fell by 59.7% and cost by 63.7%, to $0.032 and 8.4 s per contract.", indent=False)
    P("**To best answer RQ2:** the pipeline more than halves the token consumption, cost and latency of "
      "source-level vulnerability detection. The monetary saving depends on how a detector's pricing weights "
      "input against output, so token count and latency are the portable benefits.", indent=False)
    P("**RQ3 — Detection effectiveness.** F1-score rose from 0.342 to 0.693, agreement from 0.642 to 0.801 and "
      "kappa from 0.097 to 0.549, with misses falling from 314 to 104 and false positives from 259 to 214; six "
      "categories improved and two regressed.", indent=False)
    P("**To best answer RQ3:** detection improves rather than degrades, and both error types fall together "
      "(p about 3.7 × 10⁻²⁶; F1-score 0.689 on the contracts never used in development). The accuracy is carried "
      "by the calibrated prompt and the token saving by the slice, and the two compose.", indent=False)

    # ---------------------------------------------------------------- V
    H1('Limitations and Threats to Validity')
    P("The results come from one detector, one benchmark sample and one run per arm. This section first "
      "addresses the strength of the detection results and the gap between token and cost savings, then "
      "design issues exposed by the evaluation, and finally threats arising from the validation criterion, "
      "the sample, the taxonomy and the detector.", indent=False)
    P("*What the treatment combines.* Arm B changes both the input and the prompt, so the headline compares "
      "the pipeline against ordinary practice rather than the slice alone. Held to one prompt, the slice left "
      "detection unchanged (p = 1.00) while still cutting tokens, so the saving is the slice's and the "
      "accuracy the prompt's. Each arm ran once; three repetitions of one configuration varied by 4.2 points "
      "of agreement, an order of magnitude below the effect reported here.")
    P("*Two categories the pipeline does not solve.* Front running is the clearest failure: Arm B marks none "
      "of its 15 positives, trading 132 false positives for 14 at the cost of every true detection. That "
      "category comes from a single analyser in the reference and has no lexical signal: the approve "
      "allowance race appears in 164 of 200 contracts and predicts the label with precision 0.04. Time "
      "manipulation moves the other way, recovering misses while raising false positives from 11 to 50. "
      "Library collapse also recognises constructs by name, so a modified implementation under a standard "
      "name would be collapsed as well.")
    P("*Validity.* DIVE labels whole contracts, so full retention means that each positive contract keeps some "
      "block tagged with the category, not necessarily the vulnerable statements, and the labels reflect a "
      "consensus of static analysers rather than audited ground truth. The anchors were tuned on the "
      "development subset, so the whole-sample figures are in part an in-sample fit; the 130 contracts of the "
      "final round, never inspected during development, are therefore reported separately and give the same "
      "result.")
    P("*Scope.* The anchors cover DASP categories 1–8, the categories DIVE annotates; defects outside this "
      "taxonomy, or that span several interacting contracts, are not targeted. A single proprietary detector "
      "without sampling control was used, so transfer to other detectors remains untested.")

    # ---------------------------------------------------------------- VI
    H1('Conclusion and Future Work')
    P("This paper addressed the token cost of smart contract vulnerability detection with AnchorSlice, a "
      "lexical slicing stage that reduces a contract to the fragments able to host each DASP category. On 200 "
      "DIVE contracts it retained all 463 labelled category instances at 56.5% of source characters and "
      "7.6 ms per contract, and against ordinary practice it cut token consumption by 55.2%, cost by 63.7% "
      "and runtime by 59.7% while raising F1-score from 0.342 to 0.693 and agreement from 0.642 to 0.801. "
      "Because the slicer needs no model and no compilation, it can be placed in front of any source-level "
      "detector at negligible cost.",
      indent=False)
    P("Future work will add a tag-free arm to separate code removal from category hints, a selectivity "
      "threshold that suppresses over-broad anchors such as DoS, validation on a held-out DIVE split with "
      "repeated runs, and evaluation in front of other detectors, including open-weight models and LineGuard.")

def reference_list():
    BODY.append(para([run('References', 20, caps=True)], jc='center', sb=160, sa=80, keep=True))
    for n, key in enumerate(CITED, 1):
        text, (kind, target) = REFS[key]
        if kind == 'doi':
            url, shown, lead = 'https://doi.org/' + target, target, ', doi: '
        elif kind == 'arxiv':
            url, shown, lead = 'https://arxiv.org/abs/' + target, 'arXiv:' + target, ', '
        else:
            url, shown, lead = target, target, '. [Online]. Available: '
        runs = [run('[%d]\t' % n, 16)] + rich(text, 16) + [run(lead, 16)]
        runs.append(link_external(url, run(shown, 16, color=LINK)))
        if kind != 'url':
            runs.append(run('.', 16))
        BODY.append(para(runs, jc='both', li=340, hang=340, sa=30, bookmark='ref_' + key))

# ================================================================= PACKAGE
NUMBERING = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>'
    '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
    '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="300" w:hanging="200"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr></w:lvl>'
    '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')

STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
    '<w:sz w:val="20"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
    '</w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/></w:style></w:styles>')

def build():
    # title block: single column, closed by a continuous section break
    BODY.append(para([run(TITLE, 36, b=True)], jc='center', sa=180))
    BODY.append(author_table(AUTHORS))
    BODY.append(para([], sect=sectpr(1)))
    BODY.append(para([run('Abstract—', 18, b=True, i=True), run(ABSTRACT, 18, b=True)],
                     ind=200, sb=60, sa=60))
    BODY.append(para([run('Keywords—', 18, b=True, i=True), run(KEYWORDS, 18, i=True)],
                     ind=200, sb=60, sa=120))
    build_content()
    reference_list()

    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
           '<w:body>' + ''.join(BODY) + sectpr(2) + '</w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
    drels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="%sstyles" Target="styles.xml"/>' % R,
             '<Relationship Id="rId2" Type="%snumbering" Target="numbering.xml"/>' % R]
    drels += ['<Relationship Id="%s" Type="%simage" Target="media/image%d.png"/>' % (rid, R, n)
              for rid, _p, n in _IMG]
    drels += ['<Relationship Id="%s" Type="%shyperlink" Target="%s" TargetMode="External"/>' % (rid, R, x(url))
              for rid, url in EXT_LINKS]
    drels.append('</Relationships>')

    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', doc)
        z.writestr('word/_rels/document.xml.rels', ''.join(drels))
        z.writestr('word/styles.xml', STYLES)
        z.writestr('word/numbering.xml', NUMBERING)
        for _rid, p, n in _IMG:
            z.writestr('word/media/image%d.png' % n, open(p, 'rb').read())
    words = len(re.sub(r'<[^>]+>', ' ', ''.join(BODY)).split())
    print('docx written: %s (%.0f KB), %d references, %d links, ~%d words'
          % (os.path.basename(OUT), os.path.getsize(OUT) / 1024, len(CITED), len(EXT_LINKS), words))

if __name__ == '__main__':
    build()
