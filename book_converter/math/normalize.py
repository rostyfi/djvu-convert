r"""LaTeX -> mathtext normalization.

mathtext supports only a subset of LaTeX (no \begin{...} environments, and
no \tfrac/\pmb/\boxed/\textcolor/...), so normalize_tex() translates or
strips unsupported commands. Environments are handled in environments.py.
"""

import re


def _find_command(tex, cmd):
    """Position of cmd as a whole word, or -1."""
    m = re.search(re.escape(cmd) + r"(?![a-zA-Z])", tex)
    return m.start() if m else -1


def _read_group(tex, pos):
    """Read a {...} group at pos (skipping whitespace).

    Returns (content, end_pos); content is None if there is no group.
    """
    while pos < len(tex) and tex[pos].isspace():
        pos += 1
    if pos < len(tex) and tex[pos] == "{":
        depth = 0
        for i in range(pos, len(tex)):
            if tex[i] == "{":
                depth += 1
            elif tex[i] == "}":
                depth -= 1
                if depth == 0:
                    return tex[pos + 1:i], i + 1
        return tex[pos + 1:], len(tex)  # unbalanced — take the rest
    return None, pos


def _read_opt_group(tex, pos):
    """Read a [...] group at pos; returns (content, end_pos) or (None, pos)."""
    while pos < len(tex) and tex[pos].isspace():
        pos += 1
    if pos < len(tex) and tex[pos] == "[":
        end = tex.find("]", pos)
        if end != -1:
            return tex[pos + 1:end], end + 1
    return None, pos


def _remove_command(tex, cmd, max_groups):
    """Remove cmd and up to max_groups following [...] / {...} groups."""
    while True:
        idx = _find_command(tex, cmd)
        if idx == -1:
            return tex
        end = idx + len(cmd)
        consumed = 0
        while consumed < max_groups:
            _, end_opt = _read_opt_group(tex, end)
            if end_opt > end:
                end = end_opt
                consumed += 1
                continue
            content, end_req = _read_group(tex, end)
            if content is not None:
                end = end_req
                consumed += 1
            else:
                break
        tex = tex[:idx] + tex[end:]


def _keep_arg_command(tex, cmd, arg_index, max_req):
    """Replace \\cmd{...}... with the content of one of its {...} arguments."""
    while True:
        idx = _find_command(tex, cmd)
        if idx == -1:
            return tex
        end = idx + len(cmd)
        groups = []
        while len(groups) < max_req:
            _, end_opt = _read_opt_group(tex, end)
            if end_opt > end:
                end = end_opt
                continue
            content, end_req = _read_group(tex, end)
            if content is not None:
                groups.append(content)
                end = end_req
            else:
                break
        if len(groups) <= arg_index:
            tex = tex[:idx] + tex[idx + len(cmd):]
        else:
            tex = tex[:idx] + groups[arg_index] + tex[end:]


def _replace_cmd_with(tex, cmd, text):
    """Replace \\cmd{...} (or a bare \\cmd) with a fixed text."""
    while True:
        idx = _find_command(tex, cmd)
        if idx == -1:
            return tex
        pos = idx + len(cmd)
        content, end = _read_group(tex, pos)
        if content is None:
            tex = tex[:idx] + text + tex[pos:]
        else:
            tex = tex[:idx] + text + tex[end:]


def _strip_cmd_keep_group(tex, cmd):
    """Remove cmd, keeping the content of a following {...} group (if any)."""
    while True:
        idx = _find_command(tex, cmd)
        if idx == -1:
            return tex
        pos = idx + len(cmd)
        content, end = _read_group(tex, pos)
        if content is not None:
            tex = tex[:idx] + content + tex[end:]
        else:
            tex = tex[:idx] + tex[pos:]


# Commands removed together with their arguments: cmd -> max group count.
_TEX_REMOVE_CMD = {
    r"\label": 1, r"\tag": 1, r"\tag*": 1, r"\intertext": 1, r"\shortintertext": 1,
    r"\footnote": 1, r"\marginpar": 1, r"\caption": 1, r"\index": 1, r"\glossary": 1,
    r"\part": 1, r"\part*": 1, r"\chapter": 1, r"\chapter*": 1,
    r"\section": 1, r"\section*": 1, r"\subsection": 1, r"\subsection*": 1,
    r"\subsubsection": 1, r"\subsubsection*": 1, r"\paragraph": 1, r"\subparagraph": 1,
    r"\include": 1, r"\input": 1, r"\documentclass": 2, r"\usepackage": 2,
    r"\newcommand": 4, r"\renewcommand": 4, r"\providecommand": 4,
    r"\DeclareMathOperator": 2, r"\DeclareMathOperator*": 2,
    r"\def": 1, r"\let": 1,
    r"\noalign": 1, r"\cline": 1, r"\cmidrule": 2, r"\rule": 2,
    r"\setlength": 2, r"\addtolength": 2, r"\settowidth": 2,
    r"\enlargethispage": 2, r"\thispagestyle": 1, r"\pagestyle": 1,
    r"\markboth": 2, r"\markright": 1, r"\addcontentsline": 3,
    r"\bibliography": 1, r"\bibliographystyle": 1,
    r"\rowcolor": 1, r"\cellcolor": 1, r"\vadjust": 1, r"\special": 1, r"\mark": 1,
    r"\aftergroup": 1, r"\typeout": 1, r"\message": 1, r"\errmessage": 1,
    r"\errhelp": 1, r"\wlog": 1, r"\show": 1, r"\showthe": 1, r"\showbox": 1,
    r"\showlists": 1, r"\color": 2, r"\pagecolor": 1,
    r"\usefont": 4, r"\fontsize": 2, r"\fontfamily": 1, r"\fontseries": 1,
    r"\fontshape": 1,
    # no-argument commands that must simply go away
    r"\footnotemark": 0, r"\hline": 0, r"\hhline": 0, r"\global": 0, r"\long": 0,
    r"\outer": 0, r"\protected": 0, r"\expandafter": 0, r"\noexpand": 0,
    r"\makeatletter": 0, r"\makeatother": 0, r"\endinput": 0,
    r"\tracingonline": 0, r"\tracingmacros": 0, r"\tracingstats": 0,
    r"\tracingparagraphs": 0, r"\tracingpages": 0, r"\tracingoutput": 0,
    r"\tracinglostchars": 0, r"\tracingcommands": 0, r"\tracingrestores": 0,
    r"\tracingassigns": 0, r"\tracinggroups": 0, r"\tracingifs": 0,
    r"\tracingtokens": 0, r"\tracingedges": 0, r"\tracingall": 0, r"\tracingnone": 0,
    r"\batchmode": 0, r"\errorstopmode": 0, r"\nonstopmode": 0, r"\scrollmode": 0,
    r"\pausing": 0, r"\csname": 0, r"\endcsname": 0, r"\begingroup": 0, r"\endgroup": 0,
    r"\displaystyle": 0, r"\textstyle": 0, r"\scriptstyle": 0, r"\scriptscriptstyle": 0,
    r"\limits": 0, r"\nolimits": 0, r"\displaylimits": 0,
    r"\Huge": 0, r"\huge": 0, r"\LARGE": 0, r"\Large": 0, r"\large": 0,
    r"\small": 0, r"\footnotesize": 0, r"\scriptsize": 0, r"\tiny": 0, r"\normalsize": 0,
    r"\mathnormal": 0, r"\boldmath": 0, r"\unboldmath": 0, r"\mathstrut": 0, r"\strut": 0,
    r"\noindent": 0, r"\centering": 0, r"\raggedright": 0, r"\raggedleft": 0,
    r"\justifying": 0, r"\par": 0, r"\indent": 0, r"\raggedbottom": 0, r"\flushbottom": 0,
    r"\pagebreak": 0, r"\newpage": 0, r"\clearpage": 0, r"\nopagebreak": 0,
    r"\nonumber": 0, r"\notag": 0, r"\jot": 0, r"\relax": 0, r"\item": 0,
    r"\allowbreak": 0, r"\nobreak": 0, r"\dotfill": 0, r"\hdashline": 0,
    r"\toprule": 0, r"\midrule": 0, r"\bottomrule": 0, r"\choose": 0,
    r"\overwithdelims": 0, r"\atopwithdelims": 0, r"\abovewithdelims": 0,
    r"\hfil": 0, r"\hfill": 0, r"\hfilneg": 0, r"\hss": 0,
    r"\vfil": 0, r"\vfill": 0, r"\vfilneg": 0, r"\vss": 0,
    r"\vtop": 0, r"\vbox": 0, r"\vcenter": 0, r"\span": 0, r"\omit": 0,
    r"\tabskip": 0, r"\multispan": 0, r"\hidewidth": 0,
    r"\unskip": 0, r"\unpenalty": 0, r"\unkern": 0,
    r"\mathchoice": 0, r"\mathpalette": 0, r"\mathcode": 0, r"\catcode": 0,
    r"\sfcode": 0, r"\lccode": 0, r"\uccode": 0, r"\char": 0, r"\symbol": 0,
    r"\printindex": 0, r"\listoffigures": 0, r"\listoftables": 0,
    r"\tableofcontents": 0, r"\appendix": 0, r"\frontmatter": 0, r"\mainmatter": 0,
    r"\backmatter": 0, r"\sloppy": 0, r"\fussy": 0, r"\onecolumn": 0, r"\twocolumn": 0,
    r"\selectfont": 0, r"\samepage": 0,
}

# \cmd{...} -> keep only one argument's content: (cmd, arg_index, max_req)
_TEX_KEEP_ARG_CMD = [
    (r"\boxed", 0, 1), (r"\fbox", 0, 1), (r"\Aboxed", 0, 1), (r"\framebox", 0, 1),
    (r"\underline", 0, 1), (r"\uline", 0, 1), (r"\uuline", 0, 1), (r"\uwave", 0, 1),
    (r"\sout", 0, 1), (r"\xout", 0, 1), (r"\cancel", 0, 1), (r"\bcancel", 0, 1),
    (r"\xcancel", 0, 1),
    (r"\phantom", 0, 1), (r"\hphantom", 0, 1), (r"\vphantom", 0, 1), (r"\smash", 0, 1),
    (r"\mathclap", 0, 1), (r"\mathllap", 0, 1), (r"\mathrlap", 0, 1),
    (r"\overbrace", 0, 1), (r"\underbrace", 0, 1), (r"\overgroup", 0, 1),
    (r"\undergroup", 0, 1), (r"\overlinesegment", 0, 1), (r"\underlinesegment", 0, 1),
    (r"\wideparen", 0, 1), (r"\widering", 0, 1),
    (r"\textcolor", 1, 2), (r"\colorbox", 1, 2), (r"\href", 1, 2),
    (r"\url", 0, 1), (r"\nolinkurl", 0, 1),
    (r"\multicolumn", 2, 3), (r"\raisebox", 1, 2),
    (r"\hbox", 0, 1), (r"\vbox", 0, 1), (r"\ensuremath", 0, 1),
]

# \cmd{...} -> fixed text (unresolved references)
_TEX_REPLACE_WITH = {
    r"\ref": "?", r"\eqref": "(?)", r"\pageref": "?", r"\cite": "?", r"\nocite": "?",
}

# Simple command renames: cmd -> replacement
_TEX_CMD_MAP = {
    r"\tfrac": r"\frac", r"\cfrac": r"\frac", r"\dbinom": r"\binom", r"\tbinom": r"\binom",
    r"\pmb": r"\mathbf", r"\bm": r"\mathbf",
    r"\textbf": r"\text", r"\textit": r"\text", r"\texttt": r"\text",
    r"\textrm": r"\text", r"\textsf": r"\text", r"\textnormal": r"\text",
    r"\emph": r"\text", r"\mbox": r"\text",
    r"\stackrel": r"\overset", r"\mathop": r"\operatorname",
    r"\gets": r"\leftarrow", r"\iff": r"\Longleftrightarrow",
    r"\implies": r"\Longrightarrow", r"\impliedby": r"\Longleftarrow",
    r"\lnot": r"\neg", r"\owns": r"\ni",
    r"\Bbbk": r"\mathbb{k}", r"\Diamond": r"\diamond", r"\square": r"\blacksquare",
    r"\j": r"\jmath",
    r"\varlimsup": r"\limsup", r"\varliminf": r"\liminf",
    r"\injlim": r"\lim", r"\projlim": r"\lim", r"\varprojlim": r"\lim", r"\varinjlim": r"\lim",
    r"\dotso": r"\dots", r"\dotsc": r"\dots", r"\dotsb": r"\dots",
    r"\dotsm": r"\dots", r"\dotsi": r"\dots",
    r"\bmod": r"\mathrm{mod}",
    r"\euro": "€", r"\yen": "¥", r"\cent": "¢", r"\pounds": "£",
    r"\textregistered": "®", r"\textdegree": "°", r"\textcelsius": r"\text{°C}",
    r"\textsterling": "£", r"\textyen": "¥",
    r"\textbackslash": r"\backslash", r"\textbar": "|",
    r"\textless": "<", r"\textgreater": ">",
    r"\textbraceleft": r"\{", r"\textbraceright": r"\}",
    r"\textasciicircum": "^", r"\textasciitilde": "~", r"\textquotedblleft": '"',
    r"\eth": "ð", r"\Eth": "Ð",
    r"\circledast": r"\odot", r"\circledcirc": r"\circ", r"\circleddash": r"\ominus",
    r"\boxplus": r"\oplus", r"\boxminus": r"\ominus", r"\boxtimes": r"\otimes",
    r"\boxdot": r"\odot",
    r"\Cap": r"\cap", r"\Cup": r"\cup",
    r"\barwedge": r"\wedge", r"\veebar": r"\vee",
    r"\therefore": r"\Rightarrow", r"\because": r"\Leftarrow",
    r"\land": r"\wedge", r"\lor": r"\vee",
    r"\divides": r"\mid", r"\Vert": r"\|",
    r"\arrowvert": "|", r"\Arrowvert": r"\|", r"\bracevert": "|",
    r"\coloneqq": ":=", r"\eqqcolon": ":=",
    r"\bgroup": "{", r"\egroup": "}",
    r"\newline": r"\\", r"\cr": r"\\", r"\crcr": r"\\", r"\tabularnewline": r"\\",
    r"\argmax": r"\operatorname{argmax}", r"\argmin": r"\operatorname{argmin}",
}


def _xarrow(arrow):
    """Replacement factory for \\xrightarrow[under]{over} and friends."""
    def repl(m):
        under, over = m.group(1), m.group(2)
        out = r"\overset{" + over + "}{" + arrow + "}"
        if under:
            out = r"\underset{" + under + "}{" + out + "}"
        return out
    return repl


# Regex transforms applied before the command tables: (pattern, replacement)
_TEX_SPECIAL_RES = [
    (re.compile(r"\\pmod\s*\{([^{}]*)\}"), lambda m: r"(\mathrm{mod}\ " + m.group(1) + ")"),
    (re.compile(r"\\pod\s*\{([^{}]*)\}"), lambda m: r"(\mathrm{mod}\ " + m.group(1) + ")"),
    (re.compile(r"\\xrightarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\longrightarrow")),
    (re.compile(r"\\xleftarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\longleftarrow")),
    (re.compile(r"\\xRightarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\Longrightarrow")),
    (re.compile(r"\\xLeftrightarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\Longleftrightarrow")),
    (re.compile(r"\\xmapsto\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\longmapsto")),
    (re.compile(r"\\xhookrightarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\hookrightarrow")),
    (re.compile(r"\\xhookleftarrow\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}"), _xarrow(r"\hookleftarrow")),
    (re.compile(r"\\underleftarrow\s*\{([^{}]*)\}"), lambda m: r"\leftarrow " + m.group(1)),
    (re.compile(r"\\underrightarrow\s*\{([^{}]*)\}"), lambda m: r"\rightarrow " + m.group(1)),
    (re.compile(r"\\underleftrightarrow\s*\{([^{}]*)\}"), lambda m: r"\leftrightarrow " + m.group(1)),
    (re.compile(r"\\genfrac\s*\{[^{}]*\}\s*\{[^{}]*\}\s*\{[^{}]*\}\s*\{[^{}]*\}"
                r"\s*\{([^{}]*)\}\s*\{([^{}]*)\}"),
     lambda m: r"\frac{" + m.group(1) + "}{" + m.group(2) + "}"),
    (re.compile(r"\\[bB]igg?l?\s*(?=[\\(\[\]{}|.])"), ""),
    (re.compile(r"\\[bB]iggm\s*(?=[\\(\[\]{}|.])"), lambda m: r"\mid"),
    (re.compile(r"\\hspace\*?\s*\{[^{}]*\}"), lambda m: r"\quad"),
    (re.compile(r"\\vspace\*?\s*\{[^{}]*\}"), ""),
    (re.compile(r"\\(?:kern|mkern|mskip|mspace|hskip|hglue|vglue)\s*"
                r"-?[\d.]+(?:pt|em|ex|mu|in|cm|mm|pc|sp)?\s*"), ""),
    (re.compile(r"\\(?:penalty|hyphenpenalty|exhyphenpenalty|clubpenalty|widowpenalty"
                r"|displaywidowpenalty|brokenpenalty|binoppenalty|relpenalty"
                r"|predisplaypenalty|postdisplaypenalty|interlinepenalty"
                r"|interclubpenalty|interdisplaylinepenalty|floatingpenalty"
                r"|outputpenalty|adjdemerits|doublehyphendemerits"
                r"|finalhyphendemerits|hbadness|vbadness|hfuzz|vfuzz"
                r"|pretolerance|tolerance|emergencystretch|jot|thinmuskip"
                r"|medmuskip|thickmuskip|nulldelimiterspace|delimitershortfall"
                r"|delimiterfactor|scriptspace|mathsurround|escapechar"
                r"|endlinechar|newlinechar|maxdeadcycles|showboxbreadth"
                r"|showboxdepth|time|day|month|year|deadcycles)"
                r"\s*-?[\d.]+\s*(?:pt|em|ex|mu|in|cm|mm|pc|sp)?\s*"), ""),
    (re.compile(r"\\(?:hoffset|voffset|hsize|vsize|parindent|parskip|baselineskip"
                r"|lineskip|lineskiplimit|parfillskip|leftskip|rightskip|topskip"
                r"|splittopskip|splitmaxdepth|boxmaxdepth)"
                r"\s*-?[\d.]+\s*(?:pt|em|ex|in|cm|mm|pc)?\s*"), ""),
    (re.compile(r"\\mathchoice\s*\{[^{}]*\}\s*\{([^{}]*)\}\s*\{[^{}]*\}\s*\{[^{}]*\}"), r"\1"),
    (re.compile(r"\\mathpalette\s*\{[^{}]*\}\s*\{([^{}]*)\}"), r"\1"),
    (re.compile(r"\\operatorname\*"), lambda m: r"\operatorname"),
    (re.compile(r"\\frac\s*(\d)\s*(\d)"), r"\\frac{\1}{\2}"),
    (re.compile(r"\\frac\s*\{([^{}]*)\}\s*(\d)"), r"\\frac{\1}{\2}"),
    (re.compile(r"\\frac\s*(\d)\s*\{([^{}]*)\}"), r"\\frac{\1}{\2}"),
    (re.compile(r"\\binom\s*(\d)\s*(\d)"), r"\\binom{\1}{\2}"),
    (re.compile(r"\\sqrt\s*(?!\[)\s*(\d)"), r"\\sqrt{\1}"),
    (re.compile(r"\\sqrt\[([^\]]*)\]\s*(\w)"), r"\\sqrt[\1]{\2}"),
    (re.compile(r"\\not\s*\\(in|ni|subset|subseteq|supset|supseteq|exists)\b"), r"\\not\1"),
    (re.compile(r"\\not\s*="), lambda m: r"\neq"),
]

# Fixes for commands the retry loop may still hit: cmd -> replacement
_UNKNOWN_CMD_FIX = {
    r"\argmax": r"\operatorname{argmax}", r"\argmin": r"\operatorname{argmin}",
    r"\tfrac": r"\frac", r"\cfrac": r"\frac", r"\dbinom": r"\binom", r"\tbinom": r"\binom",
    r"\pmb": r"\mathbf", r"\bm": r"\mathbf", r"\boldsymbol": r"\mathbf",
    r"\textbf": r"\text", r"\textit": r"\text", r"\texttt": r"\text",
    r"\textrm": r"\text", r"\textsf": r"\text", r"\emph": r"\text", r"\mbox": r"\text",
    r"\stackrel": r"\overset", r"\mathop": r"\operatorname",
    r"\gets": r"\leftarrow", r"\iff": r"\Longleftrightarrow",
    r"\implies": r"\Longrightarrow", r"\impliedby": r"\Longleftarrow",
    r"\lnot": r"\neg", r"\owns": r"\ni",
    r"\Bbbk": r"\mathbb{k}", r"\Diamond": r"\diamond", r"\square": r"\blacksquare",
    r"\j": r"\jmath",
    r"\varlimsup": r"\limsup", r"\varliminf": r"\liminf",
    r"\injlim": r"\lim", r"\projlim": r"\lim", r"\varprojlim": r"\lim", r"\varinjlim": r"\lim",
    r"\dotso": r"\dots", r"\dotsc": r"\dots", r"\dotsb": r"\dots",
    r"\dotsm": r"\dots", r"\dotsi": r"\dots",
    r"\euro": "€", r"\yen": "¥", r"\cent": "¢", r"\pounds": "£",
    r"\displaystyle": "", r"\textstyle": "", r"\scriptstyle": "", r"\scriptscriptstyle": "",
    r"\limits": "", r"\nolimits": "", r"\displaylimits": "",
    r"\Huge": "", r"\huge": "", r"\LARGE": "", r"\Large": "", r"\large": "", r"\small": "",
    r"\footnotesize": "", r"\scriptsize": "", r"\tiny": "", r"\normalsize": "", r"\mathnormal": "",
    r"\boldmath": "", r"\unboldmath": "", r"\mathstrut": "", r"\strut": "",
    r"\noindent": "", r"\centering": "", r"\raggedright": "", r"\raggedleft": "",
    r"\par": "", r"\indent": "", r"\pagebreak": "", r"\newpage": "", r"\clearpage": "",
    r"\nopagebreak": "", r"\hline": "", r"\jot": "", r"\relax": "", r"\item": "",
    r"\nonumber": "", r"\notag": "", r"\footnotemark": "", r"\allowbreak": "", r"\nobreak": "",
    r"\dotfill": "", r"\hdashline": "", r"\toprule": "", r"\midrule": "", r"\bottomrule": "",
    r"\choose": "", r"\label": "", r"\tag": "", r"\color": "", r"\pagecolor": "",
    r"\mathchoice": "", r"\mathpalette": "", r"\boxed": "", r"\fbox": "",
    r"\underline": "", r"\sout": "", r"\cancel": "", r"\phantom": "", r"\hphantom": "",
    r"\vphantom": "", r"\smash": "", r"\textcolor": "", r"\href": "", r"\includegraphics": "",
    r"\hspace": r"\quad",
}


def _fix_unknown_cmd(tex, cmd):
    """Best-effort fix for a command mathtext rejected (retry loop)."""
    if cmd in _UNKNOWN_CMD_FIX:
        repl = _UNKNOWN_CMD_FIX[cmd]
        return re.sub(re.escape(cmd) + r"(?![a-zA-Z])", lambda m: repl, tex)
    return _strip_cmd_keep_group(tex, cmd)


def _balance_braces(tex):
    """Balance group braces (OCR output is often broken)."""
    depth = 0
    i = 0
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            i += 2  # skip the escaped character
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth > 0:
        return tex + "}" * depth
    if depth < 0:
        return "{" * (-depth) + tex
    return tex


def _has_row_break(tex):
    """True if tex contains a top-level \\\\ (a row break outside any group)."""
    depth = 0
    i = 0
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            if i + 1 < len(tex) and tex[i + 1] == "\\" and depth == 0:
                return True
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        i += 1
    return False


def normalize_tex(tex):
    """Translate/strip the LaTeX that mathtext does not support."""
    tex = tex.strip()
    tex = re.sub(r"\\verb\*?(.)(.*?)\1", "", tex, flags=re.S)
    tex = re.sub(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{[^{}]*\}", "", tex)
    for cmd, arg_index, max_req in _TEX_KEEP_ARG_CMD:
        tex = _keep_arg_command(tex, cmd, arg_index, max_req)
    for pattern, repl in _TEX_SPECIAL_RES:
        tex = pattern.sub(repl, tex)
    for cmd in sorted(_TEX_REMOVE_CMD, key=len, reverse=True):
        tex = _remove_command(tex, cmd, _TEX_REMOVE_CMD[cmd])
    for cmd, text in _TEX_REPLACE_WITH.items():
        tex = _replace_cmd_with(tex, cmd, text)
    for cmd, repl in _TEX_CMD_MAP.items():
        tex = re.sub(re.escape(cmd) + r"(?![a-zA-Z])", lambda m: repl, tex)
    tex = tex.replace("~", r"\ ")
    tex = re.sub(r"\s+", " ", tex).strip()
    return _balance_braces(tex)

