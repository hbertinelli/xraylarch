#!/usr/bin/env python
#
# InputText for  Larch

from __future__ import print_function

from six.moves import queue

OPENS  = '{(['
CLOSES = '})]'
PARENS = dict(zip(OPENS, CLOSES))
QUOTES = '\'"'
BSLASH = '\\'
COMMENT = '#'
DBSLASH = "%s%s" % (BSLASH, BSLASH)

BLOCK_FRIENDS = {'if':    ('else', 'elif'),
                 'for':   ('else',),
                 'def':   (),
                 'try':   ('else', 'except', 'finally'),
                 'while': ('else',),
                 None: ()}

STARTKEYS = ['if', 'for', 'def', 'try', 'while']

def find_eostring(txt, eos, istart):
    """find end of string token for a string"""
    while True:
        inext = txt[istart:].find(eos)
        if inext < 0:  # reached end of text before match found
            return eos, len(txt)
        elif (txt[istart+inext-1] == BSLASH and
              txt[istart+inext-2] != BSLASH):  # matched quote was escaped
            istart = istart+inext+len(eos)
        else: # real match found! skip ahead in string
            return '', istart+inext+len(eos)-1

def is_complete(text):
    """returns whether a text of code is complete
    for strings quotes and open / close delimiters,
    including nested delimeters.
    """
    itok = istart = 0
    eos = ''
    delims = []
    while itok < len(text):
        c = text[itok]
        if c in QUOTES:
            eos = c
            if text[itok:itok+3] == c*3:
                eos = c*3
            istart = itok + len(eos)
            # leap ahead to matching quote, ignoring text within
            eos, itok = find_eostring(text, eos, istart)
        elif c in OPENS:
            delims.append(PARENS[c])
        elif c in CLOSES and len(delims) > 0 and c == delims[-1]:
            delims.pop()
        elif c == COMMENT and eos == '': # comment char outside string
            itok = len(text)
        itok += 1
    return eos=='' and len(delims)==0 and not text.rstrip().endswith(BSLASH)

def strip_comments(text, char='#'):
    """return text with end-of-line comments removed"""
    out = []
    for line in text.split('\n'):
        if line.find(char) > 0:
            i = 0
            while i < len(line):
                tchar = line[i]
                if tchar == char:
                    line = line[:i]
                    break
                elif tchar in ('"',"'"):
                    eos = line[i+1:].find(tchar)
                    if eos > 0:
                        i = i + eos
                i += 1
        out.append(line.rstrip())
    return '\n'.join(out)

def get_key(text):
    """return keyword: first word of text,
    isolating keywords followed by '(' and ':' """
    t =  text.replace('(', ' (').replace(':', ' :').strip()
    return t.split(' ', 1)[0].strip()

def block_start(text):
    """return whether a complete-extended-line of text
    starts with a block-starting keyword, one of
    ('if', 'for', 'try', 'while', 'def')
    """
    txt = strip_comments(text)
    key = get_key(txt)
    if key in STARTKEYS and txt.endswith(':'):
        return key
    return False

def block_end(text):
    """return whether a complete-extended-line of text
    starts wih block-ending keyword,
    '#end' + ('if', 'for', 'try', 'while', 'def')
    """
    txt = text.strip()
    if txt.startswith('#end') or txt.startswith('end'):
        n = 3
        if txt.startswith('#end'):
            n = 4
        key = txt[n:].split(' ', 1)[0].strip()
        if key in STARTKEYS:
            return key
    return False

BLANK_TEXT = ('', '<incomplete input>', -1)

class InputText:
    """input text for larch"""
    def __init__(self, _larch=None, **kws):
        self.queue = queue.Queue()
        self.filename = '<stdin>'
        self.lineno = 0
        self.curline = 0
        self.curtext = ''
        self.delims = []
        self._larch = _larch
        self.valid_cmds = ('print', 'run', 'show', 'help')
        self.saved_text = BLANK_TEXT

    def __len__(self):
        return self.queue.qsize()

    def get(self):
        """get compile-able block of python code"""
        out = []
        filename, linenumber = None, None
        if self.saved_text != BLANK_TEXT:
            txt, filename, lineno = self.saved_text
            out.append(txt)
        text, fn, ln, done = self.queue.get()
        out.append(text)
        if filename is None:
            filename = fn
        if linenumber is None:
            linenumber = ln

        while not done:
            if self.queue.qsize() == 0:
                self.saved_text = ("\n".join(out), filename, linenumber)
                return BLANK_TEXT
            text, fn, ln, done = self.queue.get()
            out.append(text)
        self.saved_text = BLANK_TEXT
        return ("\n".join(out), filename, linenumber)

    def clear(self):
        while not self.queue.empty():
            self.queue.get()
        self.saved_text = BLANK_TEXT

    def put(self, text, filename=None, lineno=None):
        """add line of input code text"""
        if filename is not None:
            self.filename = filename
        if lineno is not None:
            self.lineno = lineno

        if self._larch is not None:
            getsym = self._larch.symtable.get_symbol
            self.valid_cmds = getsym('_sys.valid_commands', create=True)

        for txt in text.split('\n'):
            self.lineno += 1
            if len(self.curtext) == 0:
                self.curtext = txt
                self.curline = self.lineno
            else:
                self.curtext = "%s\n%s" % (self.curtext, txt)

            if is_complete(self.curtext) and len(self.curtext)>0:
                blk_start =  block_start(self.curtext)
                if blk_start:
                    self.delims.append(blk_start)
                else:
                    blk_end = block_end(self.curtext)
                    if (blk_end and len(self.delims) > 0 and
                        blk_end == self.delims[-1]):
                        self.delims.pop()
                        if self.curtext.strip().startswith('end'):
                            nblank = self.curtext.find(self.curtext.strip())
                            self.curtext = '%s#%s' % (' '*nblank,
                                                      self.curtext.strip())

                _delim = None
                if len(self.delims) > 0:
                    _delim = self.delims[-1]

                key = get_key(self.curtext)
                ilevel = len(self.delims)
                if ilevel > 0 and (key == _delim or
                                   key in BLOCK_FRIENDS[_delim]):
                    ilevel = ilevel - 1

                sindent = ' '*4*ilevel
                pytext = "%s%s" % (sindent, self.curtext.strip())
                # look for valid commands
                if key in self.valid_cmds and '\n' not in self.curtext:
                    argtext = self.curtext.strip()[len(key):].strip()
                    if not (argtext.startswith('(') and
                            argtext.endswith(')') ):
                        pytext  = "%s%s(%s)" % (sindent, key, argtext)

                self.queue.put((pytext, self.filename, self.curline, 0==len(self.delims)))
                self.curtext = ''

    @property
    def complete(self):
        return len(self.curtext)==0 and len(self.delims)==0
