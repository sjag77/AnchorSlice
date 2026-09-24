#!/usr/bin/env python3
"""Emit the manuscript as OOXML (.docx): IEEE A4 two-column, inline figures, tables."""
import os, struct, zipfile
import build_paper as bp

EMU_PER_TWIP = 635
FULL_W_TW = 9600                     # full text width: figures span both columns

def x(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

def run(t, sz=20, b=False, i=False, caps=False):
    rpr = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
    if b: rpr += '<w:b/>'
    if i: rpr += '<w:i/>'
    if caps: rpr += '<w:smallCaps/>'
    rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, x(t))

def para(runs, jc='both', ind=0, sb=0, sa=0, hang=0, li=0, sect=None, keep=False):
    # CT_PPr child order: keepNext, keepLines, widowControl, spacing, ind, jc, sectPr
    p = '<w:pPr>'
    if keep: p += '<w:keepNext/><w:keepLines/>'
    p += '<w:widowControl/>'
    p += '<w:spacing w:before="%d" w:after="%d" w:line="240" w:lineRule="auto"/>' % (sb, sa)
    if li or hang or ind:
        if hang:
            p += '<w:ind w:left="%d" w:hanging="%d"/>' % (li, hang)
        else:
            p += '<w:ind w:left="%d" w:firstLine="%d"/>' % (li, ind)
    p += '<w:jc w:val="%s"/>' % jc
    if sect: p += sect
    p += '</w:pPr>'
    return '<w:p>%s%s</w:p>' % (p, ''.join(runs))

def sectpr(cols, space=397, cont=True):
    s = '<w:sectPr>'
    if cont: s += '<w:type w:val="continuous"/>'
    s += '<w:pgSz w:w="11906" w:h="16838"/>'
    s += '<w:pgMar w:top="1077" w:right="1021" w:bottom="1418" w:left="1021" w:header="720" w:footer="720" w:gutter="0"/>'
    if cols > 1:
        s += '<w:cols w:num="%d" w:space="%d" w:equalWidth="1"/>' % (cols, space)
    else:
        s += '<w:cols w:space="%d"/>' % space
    s += '</w:sectPr>'
    return s

def table_xml(rows, head_rows, widths):
    total = sum(widths)
    out = ['<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/>'
           '<w:tblBorders>'
           '<w:top w:val="single" w:sz="8" w:color="000000"/>'
           '<w:bottom w:val="single" w:sz="8" w:color="000000"/>'
           '</w:tblBorders>'
           '<w:tblCellMar><w:left w:w="40" w:type="dxa"/><w:right w:w="40" w:type="dxa"/></w:tblCellMar>'
           '</w:tblPr><w:tblGrid>' % total]
    for w in widths: out.append('<w:gridCol w:w="%d"/>' % w)
    out.append('</w:tblGrid>')
    for ri, r in enumerate(rows):
        head = ri < head_rows
        out.append('<w:tr><w:trPr><w:cantSplit/>%s</w:trPr>'
                   % ('<w:tblHeader/>' if head else ''))
        for ci, cell in enumerate(r):
            borders = ''
            if head:
                borders = '<w:tcBorders><w:bottom w:val="single" w:sz="8" w:color="000000"/></w:tcBorders>'
            out.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s'
                       '<w:vAlign w:val="center"/></w:tcPr>' % (widths[ci], borders))
            out.append(para([run(cell, 16, b=head)],
                            jc='left' if ci == 0 else 'right', sb=20, sa=20))
            out.append('</w:tc>')
        out.append('</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)

def image_xml(rid, path, goal_tw, name):
    d = open(path, 'rb').read()
    w, h = struct.unpack('>II', d[16:24])
    cx = goal_tw * EMU_PER_TWIP
    cy = int(cx * h / w)
    return ('<w:p><w:pPr>'
            '<w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            '<wp:extent cx="%d" cy="%d"/><wp:docPr id="%d" name="%s"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
            % (cx, cy, rid, name, rid, name, 'rId%d' % rid, cx, cy)), (w, h)

# ------------------------------------------------------------------ body
body = []

# title block (single column, continuous section break at its end)
body.append(para([run(bp.TITLE, 36, b=True)], jc='center', sa=180))

cells = []
for nm, em in bp.AUTHORS:
    c = ['<w:tc><w:tcPr><w:tcW w:w="3288" w:type="dxa"/></w:tcPr>']
    c.append(para([run(nm, 22)], jc='center'))
    for ln in ('Faculty of Computer Science and Engineering', 'Shahid Beheshti University', 'Tehran, Iran'):
        c.append(para([run(ln, 20, i=True)], jc='center'))
    c.append(para([run(em, 20)], jc='center'))
    c.append('</w:tc>')
    cells.append(''.join(c))
body.append('<w:tbl><w:tblPr><w:tblW w:w="9864" w:type="dxa"/>'
            '<w:tblCellMar><w:left w:w="60" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar>'
            '</w:tblPr><w:tblGrid><w:gridCol w:w="3288"/><w:gridCol w:w="3288"/><w:gridCol w:w="3288"/></w:tblGrid>'
            '<w:tr>' + ''.join(cells) + '</w:tr></w:tbl>')
body.append(para([], sect=sectpr(1)))          # end single-column section

rels_extra, media, rid = [], [], 10
in_figure = [False]

for it in bp.ITEMS:
    k = it[0]
    if k == 'abstract':
        body.append(para([run('Abstract—', 18, b=True, i=True), run(it[1], 18, b=True)],
                         ind=200, sb=60, sa=60))
    elif k == 'keywords':
        body.append(para([run('Keywords—', 18, b=True, i=True), run(it[1], 18, i=True)],
                         ind=200, sb=60, sa=120))
    elif k == 'h1':
        body.append(para([run('%s.  %s' % (it[1], it[2]), 20, caps=True)],
                         jc='center', sb=160, sa=80, keep=True))
    elif k == 'h2':
        body.append(para([run(it[1], 20, i=True)], jc='left', sb=100, sa=60, keep=True))
    elif k == 'h5':
        body.append(para([run(it[1], 20, caps=True)], jc='center', sb=160, sa=80, keep=True))
    elif k == 'p':
        body.append(para([run(it[1], it[3])], ind=200 if it[2] else 0))
    elif k == 'tblhead':
        body.append(para([run(it[1], 16, caps=True)], jc='center', sb=140, sa=60, keep=True))
    elif k == 'table':
        rows, cum = it[1], it[3]
        w = [cum[0]] + [cum[i] - cum[i-1] for i in range(1, len(cum))]
        body.append(table_xml(rows, it[2], w))
    elif k == 'wide_start':
        if '</w:pPr>' in body[-1]:
            body[-1] = body[-1].replace('</w:pPr>', sectpr(2) + '</w:pPr>', 1)
        else:
            body.append(para([], sect=sectpr(2)))
    elif k == 'wide_end':
        body.append(para([run('', 4)], sect=sectpr(1)))
    elif k == 'img':
        # close the two-column run so the figure can span the full text width
        if '</w:pPr>' in body[-1]:
            body[-1] = body[-1].replace('</w:pPr>', sectpr(2) + '</w:pPr>', 1)
        else:
            body.append(para([], sect=sectpr(2)))
        xml, _ = image_xml(rid, it[1], FULL_W_TW, 'fig%d' % rid)
        body.append(xml)
        in_figure[0] = True
        media.append((rid, it[1]))
        rels_extra.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
                          'officeDocument/2006/relationships/image" Target="media/image%d.png"/>'
                          % (rid, rid))
        rid += 1
    elif k == 'cap':
        # caption ends the single-column figure section; body resumes in two columns
        sect = sectpr(1) if in_figure[0] else None
        body.append(para([run(it[1], 16)], jc='center', sb=60, sa=100, sect=sect))
        in_figure[0] = False
    elif k == 'refs':
        for i, r in enumerate(it[1], 1):
            body.append(para([run('[%d]\t%s' % (i, r), 16)], li=260, hang=260, sa=30))

body.append(para([], sect=None))
DOC = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
       '<w:body>' + ''.join(body) + sectpr(2) + '</w:body></w:document>')

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Default Extension="png" ContentType="image/png"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
      'officedocument.wordprocessingml.document.main+xml"/>'
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-'
      'officedocument.wordprocessingml.styles+xml"/></Types>')

RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/></Relationships>')

DRELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
         'relationships/styles" Target="styles.xml"/>' + ''.join(rels_extra) + '</Relationships>')

STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          '<w:docDefaults><w:rPrDefault><w:rPr>'
          '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
          '<w:sz w:val="20"/></w:rPr></w:rPrDefault>'
          '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
          '</w:pPr></w:pPrDefault></w:docDefaults>'
          '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
          '<w:name w:val="Normal"/></w:style></w:styles>')

out = os.path.join(bp.HERE, 'AnchorSlice_manuscript.docx')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', CT)
    z.writestr('_rels/.rels', RELS)
    z.writestr('word/document.xml', DOC)
    z.writestr('word/_rels/document.xml.rels', DRELS)
    z.writestr('word/styles.xml', STYLES)
    for r, p in media:
        z.writestr('word/media/image%d.png' % r, open(p, 'rb').read())
print('docx written: %.0f KB, %d images, %d refs'
      % (os.path.getsize(out)/1024, len(media), len(bp.REFS)))
