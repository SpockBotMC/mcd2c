# Inspired by https://github.com/cogu/cfile

c_indent_char = '\t'

def set_indent_char(char):
    global c_indent_char
    c_indent_char = char


class blank:
    def __init__(self, num=1):
        self.indent = 0 #Irrelevant, kept because it simplifies sequences
        self.num = num

    def __str__(self):
        # Sequences automatically insert one line break for each element, so
        # we substract one line break to account for that
        return (self.num - 1) * '\n'


# line and its subclasses can be used as container classes for sequences, which
# can span multiple lines. When used on its own though it's a single line
class line:
    def __init__(self, elem, indent=0):
        self.elem = elem
        self._indent = 0
        self.indent = indent

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        if hasattr(self.elem, 'indent'):
            self.elem.indent = val
        self._indent = val

    def __str__(self):
        return f'{c_indent_char * self.indent}{self.elem}'


class statement(line):
    def __str__(self):
        return super().__str__() + ';'

class returnval(line):
    def __str__(self):
        return f'{c_indent_char * self.indent}return {self.elem};'


class typedef(line):
    def __init__(self, elem, name, indent=0):
        super().__init__(elem, indent)
        self.name = name

    def __str__(self):
        return f'{c_indent_char * self.indent}typedef {self.elem} {self.name};'


class linecomment(line):
    def __str__(self):
        return f'{c_indent_char * self.indent}// {self.elem}'


class include(line):
    def __init__(self, path, sys=False, indent=0):
        super().__init__(
            f'#include <{path}>' if sys else f'#include "{path}"', indent
        )


class preprocessor(line):
    directive = ''
    def __init__(self, val, indent=0):
        super().__init__(f'#{self.directive} {val}', indent)


class define(preprocessor):
    directive = 'define'
class indef(preprocessor):
    directive = 'ifndef'
class endif(line):
    def __init__(self, indent=0):
        super().__init__('#endif', indent)


from collections.abc import MutableSequence

# Group of elements at the same indentation level
class sequence(MutableSequence):
    def __init__(self, elems=None, indent=0):
        self.elems = [] if elems is None else elems
        self._indent = indent
        self.indent = indent

    def __getitem__(self, key):
        return self.elems[key]

    def __setitem__(self, key, item):
        if(isinstance(item, str)):
            item = line(item)
        item.indent = self.indent
        self.elems[key] = item

    def __delitem__(self, key):
        del self.elems[key]

    def __len__(self):
        return len(self.elems)

    def insert(self, key, item):
        if(isinstance(item, str)):
            item = line(item)
        item.indent = self.indent
        self.elems.insert(key, item)

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        for elem in self.elems:
            elem.indent = val
        self._indent = val

    def __str__(self):
        return '\n'.join([str(elem) for elem in self.elems])


#Like sequence, but joins on space instead of newline
class linesequence(sequence):
    def __setitem__(self, key, item):
        if(isinstance(item, str)):
            item = line(item)
        item.indent = self.indent if(isinstance(item, sequence)) else 0
        self.elems[key] = item

    def insert(self, key, item):
        if(isinstance(item, str)):
            item = line(item)
        item.indent = self.indent if(isinstance(item, sequence)) else 0
        self.elems.insert(key, item)

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        for elem in self.elems:
            elem.indent = val if(isinstance(elem, sequence)) else 0
        self._indent = val

    def __str__(self):
        i = c_indent_char * self.indent
        return i + ' '.join([str(elem) for elem in self.elems])


# Common for block comments and block scope items
class _block(sequence):
    def __init__(self, elems=None, inner_indent=1, indent=1):
        self._inner_indent = inner_indent
        super().__init__(elems, indent)

    @property
    def inner_indent(self):
        return self._inner_indent

    @inner_indent.setter
    def inner_indent(self, val):
        for elem in self.elems:
            elem.indent = self._indent + val
        self._inner_indent = val

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        for elem in self.elems:
            elem.indent = val + self._inner_indent
        self._indent = val


# Curly bracket {} grouped elements, optionally at different indentation level
# Does not indent first line, that's expected to be done by a wrapping class
# such as line, statement, or typedef
class block(_block):
    def __str__(self):
        return f'{{\n{super().__str__()}\n{self.indent * c_indent_char}}}'


# Similar to block but with block comment /* */ delimiters instead of {}
# Doesn't need to be wrapped in anything to get indentation correct
class blockcomment(_block):
    def __str__(self):
        i = self.indent * c_indent_char
        return f'{i}/*\n{super().__str__()}\n{i}*/'


class blocktype(block):
    keyword = ''
    def __init__(self, name=None, elems=None, inner_indent=1, indent=0):
        super().__init__(indent=indent, inner_indent=inner_indent, elems=elems)
        self.name = name

    def __str__(self):
        if self.name:
            return f'{self.keyword} {self.name} {super().__str__()}'
        return f'{self.keyword} {super().__str__()}'


class struct(blocktype):
    keyword = 'struct'
class union(blocktype):
    keyword = 'union'
class enum(blocktype):
    keyword = 'enum'

    def __str__(self):
        inner = ',\n'.join([str(elem) for elem in self.elems])
        i = self.indent * c_indent_char
        if self.name:
            return f'{self.keyword} {self.name} {{\n{inner}\n{i}}}'
        return f'{self.keyword} {{\n{inner}\n{i}}}'

class commablock(blocktype):
    def __str__(self):
        for elem in self.elems:
            elem.indent = self.indent + self._inner_indent
        inner = ',\n'.join([str(elem) for elem in self.elems])
        return f'{{\n{inner}\n{self.indent * c_indent_char}}}'


class conditional(block):
    keyword = ''
    def __init__(self, condition, elems=None, inner_indent=1, indent=0):
        super().__init__(indent=indent, inner_indent=inner_indent, elems=elems)
        self.condition = condition

    def __str__(self):
        i = self.indent * c_indent_char
        return f'{i}{self.keyword}({self.condition}) {super().__str__()}'

class _unspacedconditional(block):
    keyword = ''
    def __init__(self, condition, elems=None, inner_indent=1, indent=0):
        super().__init__(indent=indent, inner_indent=inner_indent, elems=elems)
        self.condition = condition

    def __str__(self):
        return f'{self.keyword}({self.condition}) {super().__str__()}'


class ifcond(conditional):
    keyword = 'if'
class nospace_ifcond(_unspacedconditional):
    keyword = 'if'
class elifcond(_unspacedconditional):
    keyword = 'else if'
class elsecond(block):
    keyword = 'else'

    def __str__(self):
        return f'{self.keyword} {super().__str__()}'

class switch(conditional):
    keyword = 'switch'

    def __str__(self):
        s = ''
        for elem in self.elems[:-1]:
            s += str(elem) if elem.fall and not len(elem) else f'{elem}\n'
        s += str(self.elems[-1])
        i = self.indent * c_indent_char
        return f'{i}{self.keyword}({self.condition}) {{\n{s}\n{i}}}'


class case(_block):
    def __init__(self, val, elems=None, fall=False, inner_indent=1, indent=0):
        super().__init__(elems, inner_indent, indent)
        self.val = val
        self.fall = fall

    def __str__(self):
        o = self.indent * c_indent_char
        i = (self.indent + self.inner_indent) * c_indent_char
        if self.fall:
            return f'{o}case {self.val}:\n{super().__str__()}'
        return f'{o}case {self.val}:\n{super().__str__()}\n{i}break;'

class defaultcase(_block):
    def __init__(self, elems=None, fall=True, inner_indent=1, indent=0):
        super().__init__(elems, inner_indent, indent)
        self.fall = fall

    def __str__(self):
        o = self.indent * c_indent_char
        i = (self.indent + self.inner_indent) * c_indent_char
        if self.fall:
            return f'{o}default:\n{super().__str__()}'
        return f'{o}default:\n{super().__str__()}\n{i}break;'

class inlineif(statement):
    keyword = 'if'
    def __init__(self, condition, elem, indent=0):
        super().__init__(elem, indent)
        self.condition = condition

    def __str__(self):
        i = c_indent_char * self.indent
        return i + f'{self.keyword}({self.condition}) {self.elem}'

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        self._indent = val

class forloop(block):
    keyword = 'for'
    def __init__(self, vars=None, cond=None, post=None, elems=None,
        inner_indent=1, indent=0):
        super().__init__(elems, inner_indent, indent)
        self.vars = '' if vars is None else vars
        self.cond = '' if cond is None else cond
        self.post = '' if post is None else post

    def __str__(self):
        l1 = f'{self.vars}; {self.cond}' if self.cond else self.vars + ';'
        l2 = f'{l1}; {self.post}' if self.post else l1 + ';'
        i = self.indent * c_indent_char
        return f'{i}{self.keyword}({l2}) {super().__str__()}'

class variable:
    def __init__(self, name, typename=None, array=0):
        self.name = name
        self.typename = typename
        self.array = array

    @property
    def decl(self):
        return variabledecl(self.name, self.typename, self.array)

    def __str__(self):
        return str(self.name)


class variabledecl(variable):
    def __str__(self):
        if self.array:
            return f'{self.typename} {self.name}[{self.array}]'
        return f'{self.typename} {self.name}'


class monop:
    op = ''
    def __init__(self, val, preop = True):
        self.val = val
        self.preop = preop

    def __str__(self):
        if self.preop:
            return f'{self.op}{self.val}'
        return f'{self.op}{self.val}'

class defop(monop):
    op = '*'
class refop(monop):
    op = '&'
class incop(monop):
    op = '++'
class decop(monop):
    op = '--'


class operator:
    op = ''
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

    def __str__(self):
        return f'{self.lvalue} {self.op} {self.rvalue}'

class assign(operator):
    op = '='
class addop(operator):
    op = '+'
class subop(operator):
    op = '-'
class mulop(operator):
    op = '*'
class addeq(operator):
    op = '+='
class subeq(operator):
    op = '-='
class eqeq(operator):
    op = '=='
class lth(operator):
    op = '<'
class ltheq(operator):
    op = '<='
class gth(operator):
    op = '>'
class gtheq(operator):
    op = '>='

class wrap:
    def __init__(self, val, invert=False):
        self.val = val
        self.invert = invert

    def __str__(self):
        if self.invert:
            return f'!({self.val})'
        return f'({self.val})'

class fcall(MutableSequence):
    def __init__(self, name, typename, args=None):
        self.name = name
        self.typename = typename
        self.args = [] if args is None else list(args)

    def __getitem__(self, key):
        return self.args[key]

    def __setitem__(self, key, item):
        self.args[key] = item

    def __delitem__(self, key):
        del self.args[key]

    def __len__(self):
        return len(self.args)

    def insert(self, key, item):
        self.args.insert(key, item)

    @property
    def decl(self):
        return fdecl(name, typename, [a.decl for a in self.args])

    def __str__(self):
        a = ', '.join([str(arg) for arg in self.args])
        return f'{self.name}({a})'


class fdecl(fcall):
    def __str__(self):
        a = ', '.join([str(arg) for arg in self.args])
        return f'{self.typename} {self.name}({a})'

class _file(sequence):
    def __init__(self, path, elems=None):
        self.path = path
        super().__init__(elems)


class cfile(_file):
    pass


import os

class hfile(_file):
    def __init__(self, path, elems=None, guard=None):
        super().__init__(path, elems)
        if guard is None:
            bn = os.path.basename(path)
            self.guard = f'{os.path.splitext(bn)[0].upper()}_H'
        else:
            self.guard = guard

    def __str__(self):
        t = sequence([indef(self.guard), define(self.guard), blank(2)])
        t.extend(self)
        t.append(endif())
        return str(t)
