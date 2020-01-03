# Midway upon the journey of our life
# I found myself within a forest dark,
# For the straight-forward pathway had been lost.

import mcd2c.cfile as c
import copy

# General ToDo:
#   ! Failed allocations in decode functions cannot recover memory. Consider
#     using calloc and expanding free functions to make 'free_'ing failed
#     decodes safe or just aborting on failed malloc
#   ! cfile needs better pointer support
#   ! cfile's fcall is a constant source of bugs because of the return type
#     argument being where most cfile classes put their "elems" argument, and
#     the "arguments" parameter being optional
#   ! Need a better mechanism for anonymous types

mcd_typemap = {}
def mc_data_name(typename):
    def inner(cls):
        mcd_typemap[typename] = cls
        return cls
    return inner


class generic_type:
    typename = ''
    postfix = ''

    def __init__(self, name, parent):
        self._name = name
        self.parent = parent
        self.internal = c.variable(name, self.typename)
        self.switched = False

    def struct_line(self):
        return c.statement(self.internal.decl)

    def enc_line(self, ret, dest, src):
        return c.statement(c.assign(
            ret, c.fcall(f'enc_{self.postfix}', 'char *', (dest, src))
        ))

    def dec_line(self, ret, dest, src):
        return c.statement(c.assign(
            ret, c.fcall(f'dec_{self.postfix}', 'char *', (f'&{dest}', src))
        ))

    def __eq__(self, value):
        return self.typename == value.typename

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.internal.name = name
        self._name = name

    def __str__(self):
        return str(self.internal)

class numeric_type(generic_type):
    size = 0

# Why does this even need to exist?
@mc_data_name('void')
class void_type(numeric_type):
    typename = 'void'
    def struct_line(self):
        return c.linecomment(f'\'{self.name}\' is a void type')

    def enc_line(self, ret, dest, src):
        return c.linecomment(f'\'{self.name}\' is a void type')

    def dec_line(self, ret, dest, src):
        return c.linecomment(f'\'{self.name}\' is a void type')

@mc_data_name('u8')
class num_u8(numeric_type):
    size = 1
    typename = 'uint8_t'
    postfix = 'byte'

@mc_data_name('i8')
class num_i8(num_u8):
    typename = 'int8_t'

@mc_data_name('bool')
class num_bool(num_u8):
    pass

@mc_data_name('u16')
class num_u16(numeric_type):
    size = 2
    typename = 'uint16_t'
    postfix = 'be16'

@mc_data_name('i16')
class num_i16(num_u16):
    typename = 'int16_t'

@mc_data_name('u32')
class num_u32(numeric_type):
    size = 4
    typename = 'uint32_t'
    postfix = 'be32'

@mc_data_name('i32')
class num_i32(num_u32):
    typename = 'int32_t'

@mc_data_name('u64')
class num_u64(numeric_type):
    size = 8
    typename = 'uint64_t'
    postfix = 'be64'

@mc_data_name('i64')
class num_i64(num_u64):
    typename = 'int64_t'

@mc_data_name('f32')
class num_float(num_u32):
    typename = 'float'
    postfix = 'bef32'

@mc_data_name('f64')
class num_double(num_u64):
    typename = 'double'
    postfix = 'bef64'

# Positions and UUIDs are broadly similar to numeric types
@mc_data_name('position')
class num_position(num_u64):
    typename = 'mc_position'
    postfix = 'position'

@mc_data_name('UUID')
class num_uuid(numeric_type):
    size = 16
    typename = 'mc_uuid'
    postfix = 'uuid'

class complex_type(generic_type):
    def size_line(self, size, src):
        return c.statement(
            c.addeq(size, c.fcall(f'size_{self.postfix}', 'size_t', (src,)))
        )

    def walk_line(self, ret, src, max_len, fail):
        assign = c.wrap(c.assign(
            ret, c.fcall(f'walk_{self.postfix}', 'int', (src, max_len))
        ))
        return c.ifcond(c.lth(assign, 0), (fail,))

@mc_data_name('varint')
class mc_varint(complex_type):
    # typename = 'int32_t'
    # postfix = 'varint'
    # All varints are varlongs until this gets fixed
    # https://github.com/PrismarineJS/minecraft-data/issues/119
    typename = 'int64_t'
    postfix = 'varlong'

@mc_data_name('varlong')
class mc_varlong(complex_type):
    typename = 'int64_t'
    postfix = 'varlong'

# Types which require some level of memory management
class memory_type(complex_type):
    def dec_line(self, ret, dest, src):
        assign = c.wrap(c.assign(ret, c.fcall(
            f'dec_{self.postfix}', 'char *', (f'&{dest}', src)
        )), True)
        return c.inlineif(assign, c.returnval('NULL'))

    def walkdec_line(self, ret, dest, src, fail):
        assign = c.wrap(c.assign(ret, c.fcall(
            f'dec_{self.postfix}', 'char *', (f'&{dest}', src)
        )), True)
        return c.ifcond(assign, (fail,))

    def free_line(self, src):
        return c.statement(
            c.fcall(f'free_{self.postfix}', 'void', (src,))
        )

@mc_data_name('string')
class mc_string(memory_type):
    typename = 'sds'
    postfix = 'string'

@mc_data_name('nbt')
class mc_nbt(memory_type):
    typename = 'nbt_node *'
    postfix = 'nbt'

@mc_data_name('optionalNbt')
class mc_optnbt(memory_type):
    typename = 'nbt_node *'
    postfix = 'optnbt'

@mc_data_name('slot')
class mc_slot(memory_type):
    typename = 'mc_slot'
    postfix = 'slot'

@mc_data_name('ingredient')
class mc_ingredient(memory_type):
    typename = 'mc_ingredient'
    postfix = 'ingredient'

@mc_data_name('entityMetadata')
class mc_metadata(memory_type):
    typename = 'mc_metadata'
    postfix = 'metadata'

@mc_data_name('tags')
class mc_itemtag_array(memory_type):
    typename = 'mc_itemtag_array'
    postfix = 'itemtag_array'

@mc_data_name('minecraft_smelting_format')
class mc_smelting(memory_type):
    typename = 'mc_smelting'
    postfix = 'smelting'


def get_type(typ, name, parent):
    # Pre-defined type, datautils.c can handle it
    if isinstance(typ, str):
        return mcd_typemap[typ](name, parent)
    # Fucking MCdata and their fucking inline types fuck
    else:
        return mcd_typemap[typ[0]](name, typ[1], parent)

def get_depth(field):
    depth = 0
    while not isinstance(field.parent, packet):
        depth += 1
        field = field.parent
    return depth

# These are generic structures that Mcdata uses to implement other types. Since
# mcdata often likes to define new types inline, rather than in the "types"
# section, we need to support them. This makes the generated code ugly and is
# a massive pain in my ass

class custom_type(complex_type):
    def __init__(self, name, data, parent):
        super().__init__(name, parent)
        self.data = data

@mc_data_name('buffer')
class mc_buffer(custom_type, memory_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.ln = get_type(data['countType'], 'len', self)
        self.base = c.variable('base', 'char *')
        self.children = [self.ln, self.base]

    def struct_line(self):
        return c.linesequence((c.struct(elems = (
            self.ln.struct_line(),
            c.statement(self.base.decl)
        )), c.statement(self.name)))

    def enc_line(self, ret, dest, src):
        seq = c.sequence()
        basevar = c.variable(f'{src}.base', 'char *')
        lenvar = c.variable(f'{src}.len', self.ln.typename)
        seq.append(self.ln.enc_line(ret, dest, lenvar))
        seq.append(c.statement(c.assign(dest, c.fcall(
            'memcpy', 'void *', (dest, basevar, lenvar)
        ))))
        return seq

    def dec_line(self, ret, dest, src):
        seq = c.sequence()
        basevar = c.variable(f'{dest}.base', 'char *')
        lenvar = c.variable(f'{dest}.len', self.ln.typename)
        seq.append(self.ln.dec_line(ret, lenvar, src))
        seq.append(c.inlineif(c.wrap(c.assign(
            basevar, c.fcall('malloc', 'void *', (lenvar,))
        ), True), c.returnval('NULL')))
        seq.append(c.statement(c.fcall('memcpy', 'void *', (
            basevar, src, lenvar
        ))))
        seq.append(c.statement(c.addeq(src, lenvar)))
        return seq

    def walk_line(self, ret, src, max_len, size, fail):
        seq = c.sequence()
        lenvar = c.variable(f'{self.name}_len', self.ln.typename)
        if isinstance(self.ln, numeric_type):
            seq.append(c.ifcond(c.lth(max_len, self.ln.size), (fail,)))
            seq.append(c.statement(c.addeq(size, self.ln.size)))
            seq.append(c.statement(c.subeq(max_len, self.ln.size)))
        else:
            seq.append(self.ln.walk_line(ret, src, max_len, fail))
            seq.append(c.statement(c.addeq(size, ret)))
            seq.append(c.statement(c.subeq(max_len, ret)))
        seq.append(c.statement(lenvar.decl))
        seq.append(self.ln.dec_line(src, lenvar, src))
        seq.append(c.ifcond(c.lth(max_len, lenvar), (fail,)))
        seq.append(c.statement(c.addeq(size, lenvar)))
        seq.append(c.statement(c.addeq(src, lenvar)))
        seq.append(c.statement(c.subeq(max_len, lenvar)))
        return seq

    def size_line(self, size, src):
        seq = c.sequence()
        lenvar = c.variable(f'{src}.len')
        if isinstance(self.ln, numeric_type):
            seq.append(c.statement(c.addeq(size, self.ln.size)))
        else:
            seq.append(self.ln.size_line(size, lenvar))
        seq.append(c.statement(c.addeq(size, lenvar)))
        return seq

    def free_line(self, src):
        return c.statement(c.fcall('free', 'void', (f'{src}.base',)))

@mc_data_name('restBuffer')
class mc_restbuffer(memory_type):
    typename = 'mc_buffer'
    postfix = 'buffer'

    def dec_line(self, ret, dest, src, endptr):
        return c.statement(c.assign(
            ret, c.fcall(f'dec_{self.postfix}', 'char *',
            (f'&{dest}', src, c.subop(endptr, ret)))
        ))

    def size_line(self, size, src):
        return c.statement(c.addeq(size, f'{src}.len'))

    def walk_line(self, ret, src, max_len, fail):
        return c.statement(c.assign(ret, max_len))

    def free_line(self, src):
        return c.statement(c.fcall('free', 'void', (f'{src}.base',)))

@mc_data_name('array')
class mc_array(custom_type, memory_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.children = []
        if 'countType' in data:
            self.self_contained = True
            self.prefixed = True
            self.external_count = None
            self.count = get_type(data['countType'], 'count', self)
            self.children.append(self.count)
            self.base = get_type(data['type'], '*base', self)
        elif isinstance(data['count'], int):
            self.self_contained = True
            self.prefixed = False
            self.external_count = None
            self.count = data['count']
            self.base = get_type(data['type'], '*base', self)
        else:
            self.self_contained = False
            self.prefixed = False
            self.compare = data['count']
            self.external_count = search_fields(
                to_snake_case(data['count']), parent
            )
            self.external_count.switched = True
            self.count = None
            # ToDo: This is a hack, cfile needs better pointer support
            self.base = get_type(data['type'], f'*{name}', self)
        self.children.append(self.base)

    def __eq__(self, value):
        if not super().__eq__(value):
            return False
        return all((
            self.self_contained == value.self_contained,
            self.external_count == value.external_count,
            self.count == value.count,
            self.base == value.base
        ))

    def struct_line(self):
        if self.self_contained:
            if self.prefixed:
                return c.linesequence((c.struct(elems = (
                    self.count.struct_line(),
                    self.base.struct_line()
                )), c.statement(self.name)))
            return c.linesequence((c.struct(elems = (
                self.base.struct_line(),
            )), c.statement(self.name)))
        return self.base.struct_line()

    def enc_line(self, ret, dest, src):
        seq = c.sequence()
        loopvar = c.variable(f'i_{get_depth(self)}', 'size_t')
        if self.self_contained:
            basevar = c.variable(f'{src}.base')
            if self.prefixed:
                countvar = c.variable(f'{src}.count')
                seq.append(self.count.enc_line(ret, dest, countvar))
            else:
                countvar = self.count
        else:
            countvar = c.variable(get_switched_path(self.compare, src.name, self, False))
            basevar = c.variable(f'{src}')
        basevar = c.variable(f'{basevar}[{loopvar}]')
        seq.append(c.forloop(
            c.assign(loopvar.decl, 0),
            c.lth(loopvar, countvar),
            c.incop(loopvar),
            (self.base.enc_line(ret, dest, basevar),)
        ))
        return seq

    def dec_line(self, ret, dest, src):
        seq = c.sequence()
        loopvar = c.variable(f'i_{get_depth(self)}', 'size_t')
        if self.self_contained:
            basevar = c.variable(f'{dest}.base')
            if self.prefixed:
                countvar = c.variable(f'{dest}.count')
                seq.append(self.count.dec_line(ret, countvar, src))
            else:
                countvar = self.count
        else:
            countvar = c.variable(get_switched_path(self.compare, dest.name, self))
            basevar = c.variable(f'{dest}')
        seq.append(c.inlineif(c.wrap(c.assign(basevar, c.fcall(
            'malloc', 'void *', (f'sizeof(*{basevar}) * {countvar}',)
        )), True), c.returnval('NULL')))
        basevar = c.variable(f'{basevar}[{loopvar}]')
        seq.append(c.forloop(
            c.assign(loopvar.decl, 0),
            c.lth(loopvar, countvar),
            c.incop(loopvar),
            (self.base.dec_line(ret, basevar, src),)
        ))
        return seq

    def size_line(self, size, src):
        seq = c.sequence()
        if self.self_contained:
            basevar = c.variable(f'{src}.base')
            if self.prefixed:
                countvar = c.variable(f'{src}.count')
                if isinstance(self.count, numeric_type):
                    seq.append(c.statement(c.addeq(size, self.count.size)))
                else:
                    seq.append(self.count.size_line(size, countvar))
            else:
                countvar = self.count
        else:
            countvar = c.variable(get_switched_path(self.compare, src.name, self, False))
            basevar = c.variable(f'{src}')
        if hasattr(self.base, 'size') and not self.base.size is None:
            seq.append(c.statement(c.addeq(
                size, c.mulop(countvar, self.base.size)
            )))
        else:
            loopvar = c.variable(f'i_{get_depth(self)}', 'size_t')
            basevar = c.variable(f'{basevar}[{loopvar}]')
            seq.append(c.forloop(
                c.assign(loopvar.decl, 0),
                c.lth(loopvar, countvar),
                c.incop(loopvar),
                (self.base.size_line(size, basevar),)
            ))
        return seq

    def walk_line(self, ret, src, max_len, size, fail):
        seq = c.sequence()
        if self.self_contained and self.prefixed:
            countvar = c.variable(f'{self.name}_count', self.count.typename)
            # Hack for arrays containing arrays
            if self.name == '*base':
                depth = 0
                parent = self.parent
                while parent.name == '*base':
                    depth += 1
                    parent = self.parent
                countvar.name = f'{self.parent.name}{depth}_count'
            if isinstance(self.count, numeric_type):
                seq.append(c.ifcond(c.lth(max_len, self.count.size), (fail,)))
                seq.append(c.statement(c.addeq(size, self.count.size)))
                seq.append(c.statement(c.subeq(max_len, self.count.size)))
            else:
                seq.append(self.count.walk_line(ret, src, max_len, fail))
                seq.append(c.statement(c.addeq(size, ret)))
                seq.append(c.statement(c.subeq(max_len, ret)))
            seq.append(c.statement(countvar.decl))
            seq.append(self.count.dec_line(src, countvar, src))
        elif self.self_contained and not self.prefixed:
            countvar = self.count
        else:
            countvar = self.external_count.internal
        if hasattr(self.base, 'size') and not self.base.size is None:
            seq.append(c.ifcond(
                c.lth(max_len, c.mulop(countvar, self.base.size)),
                (fail,)
            ))
            seq.append(c.statement(c.addeq(
                size, c.mulop(countvar, self.base.size)
            )))
            seq.append(c.statement(c.addeq(
                src, c.mulop(countvar, self.base.size)
            )))
            seq.append(c.statement(c.subeq(
                max_len, c.mulop(countvar, self.base.size)
            )))
        else:
            depth = get_depth(self)
            loopvar = c.variable(f'i_{depth}', 'size_t')
            if isinstance(self.base, custom_type):
                forelems = [self.base.walk_line(ret, src, max_len, size, fail)]
            else:
                forelems = [self.base.walk_line(ret, src, max_len, fail)]
                forelems.append(c.statement(c.addeq(size, ret)))
                forelems.append(c.statement(c.addeq(src, ret)))
                forelems.append(c.statement(c.subeq(max_len, ret)))
            seq.append(c.forloop(
                c.assign(loopvar.decl, 0),
                c.lth(loopvar, countvar),
                c.incop(loopvar, False),
                forelems
            ))

        return seq

    def free_line(self, src):
        seq = c.sequence()
        if self.self_contained:
            basevar = c.variable(f'{src}.base')
            if self.prefixed:
                countvar = c.variable(f'{src}.count')
            else:
                countvar = self.count
        else:
            countvar = c.variable(get_switched_path(
                self.compare, src.name, self, False
            ))
            basevar = c.variable(f'{src}')
        final = c.statement(c.fcall('free', 'void', (basevar,)))
        if isinstance(self.base, memory_type) or (
            hasattr(self.base, 'children') and
            check_instance(self.base.children, memory_type)
        ):
            loopvar = c.variable(f'i_{get_depth(self)}', 'size_t')
            basevar = c.variable(f'{basevar}[{loopvar}]')
            seq.append(c.forloop(
                c.assign(loopvar.decl, 0),
                c.lth(loopvar, countvar),
                c.incop(loopvar),
                (self.base.free_line(basevar),)
            ))
        seq.append(final)
        return seq

import re

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
def to_snake_case(name):
    if name is None: return None
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

# Read consecutive numeric types from a list of fields and return their
# collective size and the position they're interrupted by a non-numeric type or
# a numeric that acts as a switch, which will need to be decoded
def group_numerics_walk(fields, position):
    total = 0
    for idx, field in enumerate(fields[position:]):
        if isinstance(field, mc_bitfield):
            if any([child.switched for child in field.children]):
                return position + idx, total
            total += field.size
        elif isinstance(field, numeric_type) and not field.switched:
            total += field.size
        else:
            return position + idx, total
    return position + len(fields), total

def group_numerics_size(fields, position):
    total = 0
    for idx, field in enumerate(fields[position:]):
        if isinstance(field, numeric_type):
            total += field.size
        else:
            return position + idx, total
    return position + len(fields), total

def check_instance(fields, typ):
    for field in fields:
        if isinstance(field, typ):
            return True
        if hasattr(field, 'children') and check_instance(field.children, typ):
            return True
    else:
        return False

@mc_data_name('container')
class mc_container(custom_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.fields = []
        self.children = self.fields
        for field in data:
            try:
                fname = to_snake_case(field['name'])
            except KeyError as err:
                fname = 'anonymous'
            self.fields.append(get_type(field['type'], fname, self))
        self.complex = check_instance(self.fields, complex_type)
        if self.complex:
            self.size = None
        else:
            _, self.size = group_numerics_size(self.fields, 0)

    def __eq__(self, value):
        if not super().__eq__(value) or len(self.fields) != len(value.fields):
            return False
        return all([i == j for i, j in zip(self.fields, value.fields)])

    def struct_line(self):
        return c.linesequence((
            c.struct(elems = [f.struct_line() for f in self.fields]),
            c.statement(self.name)
        ))

    def enc_line(self, ret, dest, src):
        seq = c.sequence()
        for field in self.fields:
            v = c.variable(f'{src}.{field}', field.typename)
            seq.append(field.enc_line(ret, dest, v))
        return seq

    def dec_line(self, ret, dest, src):
        seq = c.sequence()
        for field in self.fields:
            v = c.variable(f'{dest}.{field}', field.typename)
            seq.append(field.dec_line(ret, v, src))
        return seq

    def size_line(self, size, src):
        if not self.complex:
            position, total = group_numerics_size(self.fields, 0)
            return c.statement(c.addeq(size, total))
        seq = c.sequence()
        position = 0
        endpos = len(self.fields)
        while(position < endpos):
            position, total = group_numerics_size(self.fields, position)
            if total:
                seq.append(c.statement(c.addeq(size, total)))
            if position < endpos:
                field = self.fields[position]
                position += 1
                v = c.variable(f'{src}.{field}')
                seq.append(field.size_line(size, v))
        return seq

    def walk_line(self, ret, src, max_len, size, fail):
        seq = c.sequence()
        to_free = []
        position = 0
        endpos = len(self.fields)
        while(position < endpos):
            position, total = group_numerics_walk(self.fields, position)
            if total:
                seq.append(c.ifcond(c.lth(max_len, total), (fail,)))
                seq.append(c.statement(c.addeq(size, total)))
                seq.append(c.statement(c.addeq(src, total)))
                seq.append(c.statement(c.subeq(max_len, total)))
            if position < endpos:
                fail = copy.deepcopy(fail)
                field = self.fields[position]
                position += 1
                if field.switched:
                    #ToDo: Consider giving types a walk_switched method instead
                    # of this madness
                    seq.append(c.statement(field.internal.decl))
                    if isinstance(field, numeric_type):
                        seq.append(c.ifcond(c.lth(max_len, field.size), (fail,)))
                        seq.append(c.statement(c.addeq(size, field.size)))
                        seq.append(c.statement(c.subeq(max_len, field.size)))
                    else:
                        seq.append(field.walk_line(ret, src, max_len, fail))
                        seq.append(c.statement(c.addeq(size, ret)))
                        seq.append(c.statement(c.subeq(max_len, ret)))
                    if isinstance(field, memory_type):
                        seq.append(field.walkdec_line(src, field, src, fail))
                        to_free.append(field)
                        fail = copy.deepcopy(fail)
                        fail.insert(0, field.free_line(field))
                    else:
                        seq.append(field.dec_line(src, field, src))
                elif isinstance(field, custom_type):
                    seq.append(field.walk_line(ret, src, max_len, size, fail))
                else:
                    seq.append(field.walk_line(ret, src, max_len, fail))
                    seq.append(c.statement(c.addeq(size, ret)))
                    seq.append(c.statement(c.addeq(src, ret)))
                    seq.append(c.statement(c.subeq(max_len, ret)))
        for field in to_free:
            seq.append(field.free_line(field))
        return seq

    def free_line(self, src):
        seq = c.sequence()
        for field in self.fields:
            if isinstance(field, memory_type) or (
                hasattr(field, 'children') and
                check_instance(field.children, memory_type)
            ):
                v = c.variable(f'{src}.{field}')
                seq.append(field.free_line(v))
        return seq

@mc_data_name('option')
class mc_option(custom_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.children = []
        self.opt = num_u8('opt', self)
        self.children.append(self.opt)
        self.val = get_type(data, 'val', self)
        self.children.append(self.val)

    def struct_line(self):
        return c.linesequence((c.struct(elems = (
            self.opt.struct_line(),
            self.val.struct_line()
        )), c.statement(self.name)))

    def enc_line(self, ret, dest, src):
        seq = c.sequence()
        optvar = c.variable(f'{src}.opt')
        seq.append(self.opt.enc_line(ret, dest, optvar))
        valvar = c.variable(f'{src}.val')
        seq.append(c.ifcond(optvar, (self.val.enc_line(ret, dest, valvar),)))
        return seq

    def dec_line(self, ret, dest, src):
        seq = c.sequence()
        optvar = c.variable(f'{dest}.opt')
        seq.append(self.opt.dec_line(ret, optvar, src))
        valvar = c.variable(f'{dest}.val')
        seq.append(c.ifcond(optvar, (self.val.dec_line(ret, valvar, src),)))
        return seq

    def size_line(self, size, src):
        seq = c.sequence()
        optvar = c.variable(f'{src}.opt')
        seq.append(c.statement(c.addeq(size, 1)))
        valvar = c.variable(f'{src}.val')
        ifseq = c.ifcond(optvar)
        seq.append(ifseq)
        if isinstance(self.val, numeric_type):
            ifseq.append(c.statement(c.addeq(size, self.val.size)))
        else:
            ifseq.append(self.val.size_line(size, valvar))
        return seq

    def walk_line(self, ret, src, max_len, size, fail):
        seq = c.sequence()
        seq.append(c.ifcond(c.lth(max_len, self.opt.size), (fail,)))
        optvar = c.variable(f'{self.name}_opt', self.opt.typename)
        seq.append(c.statement(optvar.decl))
        seq.append(self.opt.dec_line(src, optvar, src))
        seq.append(c.statement(c.addeq(size, self.opt.size)))
        seq.append(c.statement(c.subeq(max_len, self.opt.size)))
        ifseq = c.ifcond(optvar)
        seq.append(ifseq)
        if isinstance(self.val, custom_type):
            ifseq.append(self.val.walk_line(ret, src, max_len, size, fail))
        elif isinstance(self.val, numeric_type):
            ifseq.append(c.ifcond(c.lth(max_len, self.val.size), (fail,)))
            ifseq.append(c.statement(c.addeq(size, self.val.size)))
            ifseq.append(c.statement(c.addeq(src, self.val.size)))
            ifseq.append(c.statement(c.subeq(max_len, self.val.size)))
        else:
            ifseq.append(self.val.walk_line(ret, src, max_len, fail))
            ifseq.append(c.statement(c.addeq(size, ret)))
            ifseq.append(c.statement(c.addeq(src, ret)))
            ifseq.append(c.statement(c.subeq(max_len, ret)))
        return seq

    # Option isn't a memory type, so if free_line is called we know that val is
    # or contains one
    def free_line(self, src):
        optvar = c.variable(f'{src}.opt')
        valvar = c.variable(f'{src}.val')
        return c.ifcond(optvar, (self.val.free_line(valvar),))

def search_down(name, field):
    for child in field.children:
        if child.name == name:
            return child
        if hasattr(child, 'children'):
            ret = search_down(name, child)
            if not ret is None:
                return ret
    return None

def search_fields(name, parent):
    while True:
        for field in parent.children:
            if field.name == name:
                return field
            if hasattr(field, 'children'):
                ret = search_down(name, field)
                if not ret is None:
                    return ret
        if hasattr(parent, 'parent'):
            parent = parent.parent
        else:
            return None

def generic_size_func(app, field, size, src):
    if isinstance(field, numeric_type):
        app.append(c.statement(c.addeq(size, field.size)))
    else:
        app.append(field.size_line(size, src))

def generic_walk_func(app, field, ret, src, max_len, size, fail):
    if isinstance(field, numeric_type):
        app.append(c.ifcond(c.lth(max_len, field.size), (fail,)))
        app.append(c.statement(c.addeq(size, field.size)))
        app.append(c.statement(c.addeq(src, field.size)))
        app.append(c.statement(c.subeq(max_len, field.size)))
    else:
        if isinstance(field, custom_type):
            fail = copy.deepcopy(fail)
            app.append(field.walk_line(ret, src, max_len, size, fail))
        else:
            app.append(field.walk_line(ret, src, max_len, fail))
            app.append(c.statement(c.addeq(size, ret)))
            app.append(c.statement(c.addeq(src, ret)))
            app.append(c.statement(c.subeq(max_len, ret)))

# compare is a protodef compareTo string
# dest is a C struct/variable string to the switch variable
# By their powers combined we find our way to the switched variable
def get_switched_path(compare, dest, field, decode=True):
    rf = dest.rfind('.')
    parent = field.parent
    if isinstance(parent, packet) and decode:
        dest = dest[:dest.find('->') + 2]
    else:
        dest = dest[:dest.rfind('.')]
    for token in compare.split('/'):
        if token == '..':
            parent = parent.parent
            # Only containers count for '..' lesser types like switches and
            # arrays must be stripped away like the inconsequential trash they
            # are.
            while (
                not isinstance(parent, mc_container) and
                not isinstance(parent, packet)
            ):
                dest = dest[:dest.rfind('.')]
                parent = parent.parent
            if isinstance(parent, packet) and decode:
                dest = dest[:dest.find('->') + 2]
            else:
                dest = dest[:dest.rfind('.')]
        else:
            if isinstance(parent, packet) and decode:
                dest = f'{dest}{to_snake_case(token)}'
            else:
                dest = f'{dest}.{to_snake_case(token)}'
    return dest

# Switches can do an almost impossible to implement thing, they can move UP the
# structure hierarchy to look for values. This is... challenging to say the
# least. It would be fine if compareTo was an absolute path, but it's a
# relative path which means we have to have huge amounts of knowledge about the
# structure of the packet in order to derive the appropriate functions
#
# Moreover, mcdata uses switches to implement non-trivial optionals (optionals
# that aren't prefixed by a bool byte). A naive implementation results in some
# pretty silly data structures. We try to detect when the switch is actually an
# optional by checking all sorts of crap. Ideally we would be able to merge
# identical sequential switches but that's really hard to do with mcd2c's
# current structure
#
# I dislike protodef switches and I dislike how mcdata uses them
@mc_data_name('switch')
class mc_switch(custom_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.compare = data['compareTo']
        self.fields = []
        self.children = self.fields
        self.optional = True
        self.map = {}
        self.has_default = False
        self.default_typ = None
        self.string_switch = False
        self.isbool = False
        self.optional_case = None
        for enum, typ in data['fields'].items():
            name = 'enum_' + enum.replace(':', '_')
            field = get_type(typ, name, self)
            # Stupid hack around protodef booleans
            if enum == 'true':
                enum = '1'
                self.isbool = True
            elif enum == 'false':
                enum = '0'
                self.isbool = True
            # Relying on ordered dict, this is Python 3.7+ code lol
            self.map[int(enum) if enum.isnumeric() else enum] = field
            if not enum.isnumeric():
                self.string_switch = True
            if isinstance(field, void_type):
                continue
            self.fields.append(field)
            if self.optional and (field != self.fields[0]):
                self.optional = False
        if 'default' in data and data['default'] != 'void':
            self.has_default = True
            self.default_typ = get_type(data['default'], 'enum_def', self)
            self.fields.append(self.default_typ)
            if self.default_typ != self.fields[0]:
                self.optional = False

        if self.optional:
            for k, v in self.map.items():
                if not (isinstance(v, void_type)):
                    self.optional_case = k
                    break;
            self.fields = self.fields[:1]
            self.fields[0].name = self.name

        self.cp_short = to_snake_case(
            self.compare[self.compare.rfind('/') + 1:]
        )
        field = search_fields(self.cp_short, parent)
        if isinstance(field.parent, mc_bitfield) and not self.isbool:
            self.isbool = field.parent.field_sizes[field.name] == 1
        field.switched = True

    def struct_line(self):
        if self.optional:
            return self.fields[0].struct_line()
        return c.linesequence((
            c.union(elems = [f.struct_line() for f in self.fields]),
            c.statement(self.name)
        ))

    def enc_line(self, ret, dest, src):
        swvar = c.variable(get_switched_path(self.compare, src.name, self, False))
        if self.isbool and self.optional:
            v = c.variable(src.name)
            if self.optional_case:
                return c.ifcond(swvar, (self.fields[0].enc_line(ret, dest, v),))
            else:
                return c.ifcond(c.wrap(swvar, True), (
                    self.fields[0].enc_line(ret, dest, v),
                ))

        if not self.string_switch:
            sw = c.switch(swvar)
            completed_fields = []
            for caseval, field in self.map.items():
                for idx, temp in enumerate(completed_fields):
                    if field == temp:
                        sw.insert(idx, c.case(caseval, fall=True))
                        completed_fields.insert(idx, field)
                        break
                else:
                    cf = c.case(caseval)
                    if isinstance(field, void_type):
                        cf.append(c.linecomment('void condition'))
                    else:
                        if self.optional:
                            v = c.variable(src.name)
                        else:
                            v = c.variable(f'{src}.{field}')
                        cf.append(field.enc_line(ret, dest, v))
                    completed_fields.append(field)
                    sw.append(cf)
            if self.has_default:
                for idx, temp in enumerate(completed_fields):
                    if self.default_typ == temp:
                        sw.insert(idx, c.defaultcase())
                        break
                else:
                    df = c.defaultcase()
                    if self.optional:
                        v = c.variable(src.name)
                    else:
                        v = c.variable(f'{src}.{field}')
                    df.append(self.default_typ.enc_line(ret, dest, v))
                    sw.append(df)
            return sw
        first = True
        sw = c.linesequence()
        for caseval, field in self.map.items():
            if not self.has_default and isinstance(field, void_type):
                continue
            if first:
                cf = c.nospace_ifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swvar)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swvar)
                ), True))
            if isinstance(field, void_type):
                cf.append(c.linecomment('void condition'))
            else:
                if self.optional:
                    v = c.variable(src.name)
                else:
                    v = c.variable(f'{src}.{field}')
                cf.append(field.enc_line(ret, dest, v))
            sw.append(cf)
        if self.has_default:
            df = c.elsecond()
            if self.optional:
                v = c.variable(src.name)
            else:
                v = c.variable(f'{src}.{self.default_typ}')
            df.append(self.default_typ.enc_line(ret, dest, v))
            sw.append(df)
        return sw

    def dec_line(self, ret, dest, src):
        swvar = c.variable(get_switched_path(self.compare, dest.name, self))
        if self.isbool and self.optional:
            v = c.variable(dest.name)
            if self.optional_case:
                return c.ifcond(swvar, (self.fields[0].dec_line(ret, v, src),))
            else:
                return c.ifcond(c.wrap(swvar, True), (
                    self.fields[0].dec_line(ret, v, src),
                ))

        if not self.string_switch:
            sw = c.switch(swvar)
            completed_fields = []
            for caseval, field in self.map.items():
                for idx, temp in enumerate(completed_fields):
                    if field == temp:
                        sw.insert(idx, c.case(caseval, fall=True))
                        completed_fields.insert(idx, field)
                        break
                else:
                    cf = c.case(caseval)
                    if isinstance(field, void_type):
                        cf.append(c.linecomment('void condition'))
                    else:
                        if self.optional:
                            v = c.variable(dest.name)
                        else:
                            v = c.variable(f'{dest}.{field}')
                        cf.append(field.dec_line(ret, v, src))
                    completed_fields.append(field)
                    sw.append(cf)
            if self.has_default:
                for idx, temp in enumerate(completed_fields):
                    if self.default_typ == temp:
                        sw.insert(idx, c.defaultcase())
                        break
                else:
                    df = c.defaultcase()
                    if self.optional:
                        v = c.variable(dest.name)
                    else:
                        v = c.variable(f'{dest}.{self.default_typ}')
                    df.append(self.default_typ.dec_line(ret, v, src))
                    sw.append(df)
            return sw
        first = True
        sw = c.linesequence()
        for caseval, field in self.map.items():
            if not self.has_default and isinstance(field, void_type):
                continue
            if first:
                cf = c.nospace_ifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swvar)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swvar)
                ), True))
            if isinstance(field, void_type):
                cf.append(c.linecomment('void condition'))
            else:
                if self.optional:
                    v = c.variable(dest.name)
                else:
                    v = c.variable(f'{dest}.{field}')
                cf.append(field.dec_line(ret, v, src))
            sw.append(cf)
        if self.has_default:
            df = c.elsecond()
            if self.optional:
                v = c.variable(dest.name)
            else:
                v = c.variable(f'{dest}.{self.default_typ}')
            df.append(self.default_typ.dec_line(ret, v, src))
            sw.append(df)
        return sw

    def size_line(self, size, src):
        swpath = get_switched_path(self.compare, src.name, self, False)
        if self.isbool and self.optional:
            elems = []
            generic_size_func(elems, self.fields[0], size, src)
            if self.optional_case:
                return c.ifcond(swpath, elems)
            else:
                return c.wrap(c.ifcond(swpath, elems), True)
        if not self.string_switch:
            sw = c.switch(swpath)
            completed_fields = []
            for caseval, field in self.map.items():
                for idx, temp in enumerate(completed_fields):
                    if field == temp:
                        sw.insert(idx, c.case(caseval, fall=True))
                        completed_fields.insert(idx, field)
                        break
                else:
                    cf = c.case(caseval)
                    if isinstance(field, void_type):
                        cf.append(c.linecomment('void condition'))
                    else:
                        if self.optional:
                            v = c.variable(src.name)
                        else:
                            v = c.variable(f'{src}.{field}')
                        generic_size_func(cf, field, size, v)
                    completed_fields.append(field)
                    sw.append(cf)
            if self.has_default:
                for idx, temp in enumerate(completed_fields):
                    if self.default_typ == temp:
                        sw.insert(idx, c.defaultcase())
                        break
                else:
                    df = c.defaultcase()
                    if self.optional:
                        v = c.variable(src.name)
                    else:
                        v = c.variable(f'{src}.{self.default_typ}')
                    generic_size_func(df, self.default_typ, size, v)
                    sw.append(df)
            return sw
        first = True
        sw = c.linesequence()
        for caseval, field in self.map.items():
            if not self.has_default and isinstance(field, void_type):
                continue
            if first:
                cf = c.nospace_ifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swpath)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swpath)
                ), True))
            if isinstance(field, void_type):
                cf.append(c.linecomment('void condition'))
            else:
                if self.optional:
                    v = c.variable(src.name)
                else:
                    v = c.variable(f'{src}.{field}')
                generic_size_func(cf, field, size, v)
            sw.append(cf)
        if self.has_default:
            df = c.elsecond()
            if self.optional:
                v = c.variable(src.name)
            else:
                v = c.variable(f'{src}.{self.default_typ}')
            generic_size_func(df, self.default_typ, size, v)
            sw.append(df)
        return sw

    def walk_line(self, ret, src, max_len, size, fail):
        if self.isbool and self.optional:
            elems = []
            generic_walk_func(elems, self.fields[0], ret, src, max_len, size, fail)
            if self.optional_case:
                return c.ifcond(self.cp_short, elems)
            else:
                return c.ifcond(c.wrap(self.cp_short, True), elems)

        if not self.string_switch:
            sw = c.switch(self.cp_short)
            completed_fields = []
            for caseval, field in self.map.items():
                for idx, temp in enumerate(completed_fields):
                    if field == temp:
                        sw.insert(idx, c.case(caseval, fall=True))
                        completed_fields.insert(idx, field)
                        break
                else:
                    cf = c.case(caseval)
                    if isinstance(field, void_type):
                        cf.append(c.linecomment('void condition'))
                    else:
                        generic_walk_func(cf, field, ret, src, max_len, size, fail)
                    completed_fields.append(field)
                    sw.append(cf)
            if self.has_default:
                for idx, temp in enumerate(completed_fields):
                    if self.default_typ == temp:
                        sw.insert(idx, c.defaultcase())
                        break
                else:
                    df = c.defaultcase()
                    generic_walk_func(
                        df, self.default_typ, ret, src, max_len, size, fail
                    )
                    sw.append(df)
            return sw
        first = True
        sw = c.linesequence()
        for caseval, field in self.map.items():
            if not self.has_default and isinstance(field, void_type):
                continue
            if first:
                cf = c.nospace_ifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', self.cp_short)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', self.cp_short)
                ), True))
            if isinstance(field, void_type):
                cf.append(c.linecomment('void condition'))
            else:
                generic_walk_func(cf, field, ret, src, max_len, size, fail)
            sw.append(cf)
        if self.has_default:
            df = c.elsecond()
            generic_walk_func(
                df, self.default_typ, ret, src, max_len, size, fail
            )
            sw.append(df)
        return sw

    def free_line(self, src):
        swpath = get_switched_path(self.compare, src.name, self, False)
        # Switch is not a memory type, so if its optional and getting a
        # free_line call, then that type is a memory type or contains one
        if self.isbool and self.optional:
            if self.optional_case:
                return c.ifcond(swpath, (self.fields[0].free_line(src),))
            else:
                return c.ifcond(c.wrap(swpath, True), (
                    self.fields[0].free_line(src),
                ))

        if not self.string_switch:
            sw = c.switch(swpath)
            completed_fields = []
            for caseval, field in self.map.items():
                for idx, temp in enumerate(completed_fields):
                    if field == temp:
                        sw.insert(idx, c.case(caseval, fall=True))
                        completed_fields.insert(idx, field)
                        break
                else:
                    cf = c.case(caseval)
                    if isinstance(field, memory_type) or (
                        hasattr(field, 'children') and
                        check_instance(field.children, memory_type)
                    ):
                        if self.optional:
                            v = c.variable(src.name)
                        else:
                            v = c.variable(f'{src}.{field}')
                        cf.append(field.free_line(v))
                    else:
                        cf.append(c.linecomment('No free-able types'))
                    completed_fields.append(field)
                    sw.append(cf)
            if self.has_default:
                for idx, temp in enumerate(completed_fields):
                    if self.default_typ == temp:
                        sw.insert(idx, c.defaultcase())
                        break
                else:
                    df = c.defaultcase()
                    if isinstance(self.default_typ, memory_type) or (
                        hasattr(self.default_typ, 'children') and
                        check_instance(self.default_typ.children, memory_type)
                    ):
                        if self.optional:
                            v = c.variable(src.name)
                        else:
                            v = c.variable(f'{src}.{self.default_typ}')
                        df.append(self.default_typ.free_line(v))
                    else:
                        df.append(c.linecomment('No free-able types'))
                    sw.append(df)
            return sw
        first = True
        sw = c.linesequence()
        for caseval, field in self.map.items():
            if not self.has_default and isinstance(field, void_type):
                continue
            if first:
                cf = c.nospace_ifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swpath)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'"{caseval}"', swpath)
                ), True))
            if isinstance(field, memory_type) or (
                hasattr(field, 'children') and
                check_instance(field.children, memory_type)
            ):
                if self.optional:
                    v = c.variable(src.name)
                else:
                    v = c.variable(f'{src}.{field}')
                cf.append(field.free_line(v))
            else:
                cf.append(c.linecomment('No free-able types'))
            sw.append(cf)
        if self.has_default:
            df = c.elsecond()
            if isinstance(self.default_typ, memory_type) or (
                hasattr(self.default_typ, 'children') and
                check_instance(self.default_typ.children, memory_type)
            ):
                if self.optional:
                    v = c.variable(src.name)
                else:
                    v = c.variable(f'{src}.{self.default_typ}')
                df.append(self.default_typ.free_line(v))
            else:
                df.append(c.linecomment('No free-able types'))
            sw.append(df)
        return sw


# bitfield is a custom_type instead of complex only because it needs to fully
# handle itself for walk funcs when it contains a switched fields. Consider
# changing to complex_type if we ever improve how walk funcs are built
@mc_data_name('bitfield')
class mc_bitfield(custom_type, numeric_type):
    def __init__(self, name, data, parent):
        lookup_unsigned = {
            8: num_u8,
            16: num_u16,
            32: num_u32,
            64: num_u64
        }
        lookup_signed = {
            8: num_i8,
            16: num_i16,
            32: num_i32,
            64: num_i64
        }
        super().__init__(name, data, parent)
        total = 0
        self.fields = []
        self.mask_shift = []
        self.field_sizes = {}
        for idx, field in enumerate(data):
            total += field['size']
            if field['name'] in ('_unused', 'unused'):
                continue
            self.field_sizes[field['name']] = field['size']
            shift = 0
            for temp in data[idx+1:]:
                shift += temp['size']
            self.mask_shift.append(((1<<field['size'])-1, shift))
            numbits = (field['size'] + 7) & -8
            if field['signed']:
                self.fields.append(
                    lookup_signed[numbits](field['name'], self)
                )
            else:
                self.fields.append(
                    lookup_unsigned[numbits](field['name'], self)
                )
        self.storage = lookup_unsigned[total](self.name, self)
        self.size = total//8
        self.children = self.fields

    def struct_line(self):
        return c.linesequence((
            c.struct(elems = [f.struct_line() for f in self.fields]),
            c.statement(self.name)
        ))

    def enc_line(self, ret, dest, src):
        seq = c.sequence()
        seq.append(c.statement(c.assign(self.storage.internal.decl, 0)))
        for idx, field in enumerate(self.fields):
            mask, shift = self.mask_shift[idx]
            seq.append(c.statement(
                f'{self.storage} |= ({src}.{field}&{mask})<<{shift}'
            ))
        seq.append(self.storage.enc_line(ret, dest, self.storage.internal))
        return seq

    def dec_line(self, ret, dest, src):
        seq = c.sequence()
        seq.append(c.statement(self.storage.internal.decl))
        seq.append(self.storage.dec_line(ret, self.storage, src))
        for idx, field in enumerate(self.fields):
            mask, shift = self.mask_shift[idx]
            # I could wrap this in three more c.[func] calls or write one
            # little f-string, I go with f-string
            seq.append(c.statement(c.assign(
                f'{dest}.{field}',
                f'({self.storage}>>{shift})&{mask}'
            )))
        return seq

    # Only called if one or more fields are switched on
    def walk_line(self, ret, src, max_len, size, fail):
        seq = c.sequence()
        seq.append(c.ifcond(c.lth(max_len, self.size), (fail,)))
        seq.append(c.statement(self.storage.internal.decl))
        seq.append(c.statement(c.addeq(size, self.size)))
        seq.append(c.statement(c.subeq(max_len, self.size)))
        seq.append(self.storage.dec_line(src, self.storage, src))
        for idx, field in enumerate(self.fields):
            if not field.switched:
                continue
            mask, shift = self.mask_shift[idx]
            seq.append(c.statement(c.assign(
                field.internal.decl, f'({self.storage.name}>>{shift})&{mask}'
            )))
        return seq

@mc_data_name('particleData')
class mc_particledata(memory_type):
    typename = 'mc_particle'
    postfix = 'particledata'

    def __init__(self, name, data, parent):
        super().__init__(name, parent)
        self.compare = data['compareTo']
        self.cp_short = to_snake_case(
            self.compare[self.compare.rfind('/') + 1:]
        )
        search_fields(self.cp_short, parent).switched = True

    def dec_line(self, ret, dest, src):
        partvar = c.variable(get_switched_path(self.compare, dest.name, self))
        return c.statement(c.assign(ret, c.fcall(
            f'dec_{self.postfix}', 'char *', (f'&{dest}', src.name, partvar)
        )))

    def walk_line(self, ret, src, max_len, fail):
        assign = c.wrap(c.assign(ret, c.fcall(
            f'walk_{self.postfix}', 'int', (src, max_len, self.cp_short)
        )))
        return c.ifcond(c.lth(assign, 0), (fail,))

# ToDo: packets are containers with extra steps, we should stop duplicating
# functionality and extract their common parts into a base class
class packet:
    def __init__(self, name, full_name, fields = None):
        self.name = name
        self.full_name = full_name
        self._fields = [] if fields is None else fields
        self.children = self._fields
        self.need_free = check_instance(self._fields, memory_type)
        self.complex = check_instance(self._fields, complex_type)

    def append(self, field):
        self._fields.append(field)
        self.need_free = check_instance(self._fields, memory_type)
        self.complex = check_instance(self._fields, complex_type)

    @property
    def fields(self):
        return self._fields

    @fields.setter
    def fields(self, fields):
        self.need_free = check_instance(fields, memory_type)
        self.complex = check_instance(fields, complex_type)
        self._fields = fields

    @classmethod
    def from_proto(cls, state, direction, name, data):
        full_name = '_'.join((state, direction.lower(), name))
        pckt = cls(name, full_name)
        for field in data[1]:
            try:
                fname = to_snake_case(field['name'])
            except KeyError as err:
                fname = 'anonymous'
                #print(f'Anonymous field in: {full_name}')
            pckt.append(get_type(field['type'], fname, pckt))
        # ToDo: This is a stupid hack, should be replaced my instantiating
        # fields in init by passing something like (typ, fname) tuples instead
        # instead of instantiated fields.
        return pckt

    def gen_struct(self):
        return c.typedef(c.struct(
            elems = [f.struct_line() for f in self.fields]
        ), self.full_name)

    def gen_function_defs(self):
        src = c.variabledecl('*source', 'char')
        dest = c.variabledecl('*dest', 'char')
        pak = c.variabledecl('packet', self.full_name)
        max_len = c.variabledecl('max_len', 'size_t')
        pak_src = c.variabledecl('source', self.full_name)
        pak_dest = c.variabledecl('*dest', self.full_name)
        totalsize = c.variabledecl('total_size', 'size_t')
        if check_instance(self.fields, mc_restbuffer):
            decargs = (pak_dest, src, totalsize)
        else:
            decargs = (pak_dest, src)
        s = c.sequence([
            c.statement(c.fdecl(
                f'walk_{self.full_name}', 'int', (src, max_len)
            )),
            c.statement(c.fdecl(f'size_{self.full_name}', 'size_t', (pak,))),
            c.statement(c.fdecl(
                f'enc_{self.full_name}', 'char *', (dest, pak_src)
            )),
            c.statement(c.fdecl(f'dec_{self.full_name}', 'char *', decargs)),
        ])
        if self.need_free:
            s.append(c.statement(
                c.fdecl(f'free_{self.full_name}', 'void', (pak,))
            ))
        return s

    def gen_walkfunc(self):
        max_len = c.variable('max_len', 'size_t')
        src = c.variable('source', 'char *')

        if not self.complex:
            position, total = group_numerics_walk(self.fields, 0)
            return c.linesequence((c.fdecl(
                f'walk_{self.full_name}', 'int', (src.decl, max_len.decl)
            ), c.block((
                c.inlineif(c.lth(max_len, total), c.returnval(-1)),
                c.returnval(total)))
            ))

        ret = c.variable('ret', 'int')
        size = c.variable('size', 'int')
        #cfile lacks the capability to group variables declarations
        blk = c.block([c.statement(f'{ret.decl}, {c.assign(size, 0)}')])
        to_free = []
        fail = c.sequence([c.returnval(-1)])
        position = 0
        endpos = len(self.fields)
        while(position < endpos):
            fail = copy.deepcopy(fail)
            position, total = group_numerics_walk(self.fields, position)
            if total:
                blk.append(c.ifcond(c.lth(max_len, total), (fail,)))
                if position < endpos:
                    blk.append(c.statement(c.addeq(size, total)))
                    blk.append(c.statement(c.addeq(src, total)))
                    blk.append(c.statement(c.subeq(max_len, total)))
                else:
                    if not isinstance(blk[-1], c.sequence):
                        del blk[-3:-1]
                    blk.append(c.returnval(c.addop(size, total)))
            if position < endpos:
                field = self.fields[position]
                position += 1
                if field.switched:
                    blk.append(c.statement(field.internal.decl))
                    if isinstance(field, numeric_type):
                        blk.append(c.ifcond(c.lth(max_len, field.size), (fail,)))
                        blk.append(c.statement(c.addeq(size, field.size)))
                        blk.append(c.statement(c.subeq(max_len, field.size)))
                    else:
                        blk.append(field.walk_line(ret, src, max_len, fail))
                        blk.append(c.statement(c.addeq(size, ret)))
                        blk.append(c.statement(c.subeq(max_len, ret)))
                    if isinstance(field, memory_type):
                        blk.append(field.walkdec_line(src, field, src, fail))
                        fail = copy.deepcopy(fail)
                        fail.insert(0, field.free_line(field))
                        to_free.append(field)
                    else:
                        blk.append(field.dec_line(src, field, src))
                elif isinstance(field, custom_type):
                    blk.append(field.walk_line(ret, src, max_len, size, fail))
                    if position >= endpos:
                        blk.append(c.returnval(size))
                else:
                    blk.append(field.walk_line(ret, src, max_len, fail))
                    if position >= endpos:
                        blk.append(c.returnval(c.addop(size, ret)))
                    else:
                        blk.append(c.statement(c.addeq(size, ret)))
                        blk.append(c.statement(c.addeq(src, ret)))
                        blk.append(c.statement(c.subeq(max_len, ret)))
        for field in to_free:
            blk.append(field.free_line(field))

        return c.linesequence((
            c.fdecl(f'walk_{self.full_name}', 'int', (src.decl, max_len.decl)),
            blk
        ))

    def gen_sizefunc(self):
        pak = c.variable('packet', self.full_name)
        if not self.complex:
            position, total = group_numerics_size(self.fields, 0)
            return c.linesequence((
                c.fdecl(f'size_{self.full_name}', 'size_t', (pak.decl,)),
                c.block((c.returnval(total),))
            ))
        blk = c.block()
        position = 0
        sizevar = c.variable('size', 'size_t')
        blk.append(c.statement(c.assign(sizevar.decl, 0)))
        endpos = len(self.fields)
        while(position < endpos):
            position, total = group_numerics_size(self.fields, position)
            if total:
                if position < endpos:
                    blk.append(c.statement(c.addeq(sizevar, total)))
                else:
                    blk.append(c.returnval(c.addop(sizevar, total)))
            if position < endpos:
                field = self.fields[position]
                position += 1
                v = c.variable(f'packet.{field}')
                blk.append(field.size_line(sizevar, v))
                if position == endpos:
                    blk.append(c.returnval(sizevar))
        return c.linesequence((
            c.fdecl(f'size_{self.full_name}', 'size_t', (pak.decl,)), blk
        ))

    def gen_decfunc(self):
        dest = c.variable('packet', self.full_name)
        destptr = c.variable('*packet', self.full_name)
        src = c.variable('source', 'char *')
        blk = c.block()
        if check_instance(self.fields, mc_restbuffer):
            totalsize = c.variable('total_size', 'size_t')
            endptr = c.variable('endptr', 'char *')
            blk.append(c.statement(c.assign(
                endptr.decl, c.addop(src, totalsize)
            )))
            args = (destptr.decl, src.decl, totalsize.decl)
        else:
            args = (destptr.decl, src.decl)
        for field in self.fields:
            v = c.variable(f'{dest}->{field}', field.typename)
            if isinstance(field, mc_restbuffer):
                blk.append(field.dec_line(src, v, src, endptr))
            else:
                blk.append(field.dec_line(src, v, src))
        blk.append(c.returnval(src))
        return c.linesequence((c.fdecl(
            f'dec_{self.full_name}', 'char *', args
        ), blk))

    def gen_encfunc(self):
        dest = c.variable('dest', 'char *')
        src = c.variable('source', self.full_name)
        blk = c.block()
        for field in self.fields:
            v = c.variable(f'{src}.{field}', field.typename)
            blk.append(field.enc_line(dest, dest, v))
        blk.append(c.returnval(dest))
        return c.linesequence((c.fdecl(
            f'enc_{self.full_name}', 'char *', (dest.decl, src.decl)
        ), blk))

    def gen_freefunc(self):
        pak = c.variable('packet', self.full_name)
        blk = c.block()
        for field in self.fields:
            if isinstance(field, memory_type) or (
                hasattr(field, 'children') and
                check_instance(field.children, memory_type)
            ):
                v = c.variable(f'packet.{field}')
                blk.append(field.free_line(v))
        return c.linesequence((
            c.fdecl(f'free_{self.full_name}', 'void', (pak.decl,)), blk
        ))

    def gen_generic_decode(self):
        seq = c.sequence()
        destvar = c.variable('dest', 'void *')
        srcvar = c.variable('src', 'char *')
        lenvar = c.variable('len', 'size_t')
        if check_instance(self.fields, mc_restbuffer):
            args = (destvar, srcvar, lenvar)
        else:
            args = (destvar, srcvar)
        seq.append(c.inlineif(
            c.noteq(c.fcall(f'walk_{self.full_name}', '', (srcvar, lenvar)), lenvar),
            c.returnval('NULL')
        ))
        seq.append(c.inlineif(c.wrap(c.assign(destvar, c.fcall(
            'malloc', 'void *', (f'sizeof({self.full_name})',)
        )), True), c.returnval('NULL')))
        seq.append(c.statement(c.fcall(f'dec_{self.full_name}', '', args)))
        return seq



import minecraft_data

def gen_enums(enums):
    seq = c.sequence()
    for state, dir_enum in enums.items():
        for direction, names in dir_enum.items():
            if names:
                enum = c.enum(f'{state}_{direction.lower()}_ids')
                for name in names:
                    enum.append(c.line(name))
                seq.append(c.statement(enum))
                seq.append(c.blank())
    return seq

def gen_stringtables(sub_stringtables):
    seq = c.sequence()
    for state in "handshaking", "status", "login", "play":
        for direction in "toClient", "toServer":
            if sub_stringtables[state][direction]:
                direct = direction.lower()
                v = c.variabledecl(f'*{state}_{direct}_strings[]', 'const char')
                seq.append(c.statement(c.assign(v, sub_stringtables[state][direction])))
                seq.append(c.blank())
    return seq

def gen_toclient_decode(org_packets):
    blk = c.block()
    idvar = c.variable('id', 'int32_t')
    statevar = c.variable('state', 'int')
    destvar = c.variable('dest', 'void *')
    srcvar = c.variable('src', 'char *')
    lenvar = c.variable('len', 'size_t')
    blk.append(c.statement(destvar.decl))
    statesw = c.switch(statevar)
    blk.append(statesw)
    for state in 'status', 'login', 'play':
        statecase = c.case(f'{state}_id')
        statesw.append(statecase)
        idsw = c.switch('id')
        statecase.append(idsw)
        for packet in org_packets[state]['toClient']:
            idsw.append(c.case(
                f'{packet.full_name}_id', packet.gen_generic_decode()
            ))
        idsw.append(c.defaultcase((c.returnval('NULL'),)))
    statesw.append(c.defaultcase((c.returnval('NULL'),)))
    blk.append(c.returnval(destvar))
    return c.linesequence((c.fdecl(
        f'generic_toclient_decode', 'void *',
        (statevar.decl, idvar.decl, srcvar.decl, lenvar.decl)
    ), blk))

def run(version):
    data = minecraft_data(version).protocol
    hdr = c.hfile(version.replace('.', '_') + '_proto.h')
    hdr.guard = 'H_' + hdr.guard
    comment = c.blockcomment((
        c.line('This file was generated by mcd2c.py'),
        c.line('It should not be edited by hand'),
    ))
    hdr.append(comment)
    hdr.append(c.blank())
    hdr.append(c.include('stddef.h', True))
    hdr.append(c.include('sds.h'))
    hdr.append(c.include('datautils.h'))
    hdr.append(c.blank())

    impl = c.cfile(version.replace('.', '_') + '_proto.c')
    impl.append(comment)
    impl.append(c.blank())
    impl.append(c.include("stdlib.h", True))
    impl.append(c.include("string.h", True))
    impl.append(c.blank())
    impl.append(c.include(hdr.path))
    impl.append(c.blank())

    packets = []


    import operator
    enums = {}
    main_stringtable = c.commablock()
    max_table = c.commablock()
    sub_stringtables = {}
    org_packets = {}
    for state in "handshaking", "status", "login", "play":
        enums[state] = {}
        sub_stringtables[state] = {}
        org_packets[state] = {}
        for direction in "toClient", "toServer":
            enums[state][direction] = []
            sub_stringtables[state][direction] = c.commablock()
            org_packets[state][direction] = []
            packet_map = data[state][direction]['types']['packet'][1][1]['type'][1]['fields']
            enum_map = data[state][direction]['types']['packet'][1][0]['type'][1]['mappings']
            for name, id in packet_map.items():
                pd = data[state][direction]['types'][id]
                pak = packet.from_proto(state, direction, name, pd)
                packets.append(pak)
                org_packets[state][direction].append(pak)
            temp = [(packet_id, name) for packet_id, name in enum_map.items()]
            temp.sort(key = operator.itemgetter(0))
            direct = direction.lower()
            for packet_id, name in temp:
                enums[state][direction].append(
                    f'{state}_{direct}_{name}_id'
                )
                sub_stringtables[state][direction].append(
                    c.line(f'"{state}_{direct}_{name}"')
                )
            if temp:
                main_stringtable.append(
                    c.line(f'[{state}_id][{direct}_id] = {state}_{direct}_strings')
                )
            max_table.append(
                c.line(f'[{state}_id][{direct}_id] = {state}_{direct}_max')
            )
            enums[state][direction].append(f'{state}_{direct}_max')

    hdr.append(c.statement(c.enum('protocol_direction_id', (
        c.line('toclient_id'),
        c.line('toserver_id'),
        c.line('protocol_direction_max'),
    ))))
    hdr.append(c.blank())
    hdr.append(c.statement(c.enum('protocol_state_id', (
        c.line('handshaking_id',),
        c.line('status_id',),
        c.line('login_id',),
        c.line('play_id'),
        c.line('protocol_state_max'),
    ))))
    hdr.append(c.blank())
    hdr.append(gen_enums(enums))


    impl.append(gen_stringtables(sub_stringtables))
    impl.append(c.statement(c.assign(c.variabledecl(
        '**protocol_strings[protocol_state_max][protocol_direction_max]', 'const char'
    ), main_stringtable)))
    impl.append(c.blank())
    impl.append(c.statement(c.assign(c.variabledecl(
        'protocol_max_ids[protocol_state_max][protocol_direction_max]', 'const int'
    ), max_table)))

    # ToDo: This is lazy but I'm tired
    hdr.append(c.statement('extern const char *handshaking_toserver_strings[]'))
    hdr.append(c.statement('extern const char *status_toclient_strings[]'))
    hdr.append(c.statement('extern const char *login_toclient_strings[]'))
    hdr.append(c.statement('extern const char *login_toserver_strings[]'))
    hdr.append(c.statement('extern const char *play_toclient_strings[]'))
    hdr.append(c.statement('extern const char *play_toserver_strings[]'))
    hdr.append(c.statement('extern const char **protocol_strings[protocol_state_max][protocol_direction_max]'))
    hdr.append(c.statement('extern const int protocol_max_ids[protocol_state_max][protocol_direction_max]'))
    hdr.append(c.statement('void *generic_toclient_decode(int state, int32_t id, char * src, size_t len)'))
    hdr.append(c.blank())

    for p in packets:
        if p.fields:
            hdr.append(c.blank())
            hdr.append(p.gen_struct())
            hdr.append(c.blank())
            hdr.append(p.gen_function_defs())

            impl.append(c.blank())
            impl.append(p.gen_walkfunc())
            impl.append(c.blank())
            impl.append(p.gen_sizefunc())
            impl.append(c.blank())
            impl.append(p.gen_decfunc())
            impl.append(c.blank())
            impl.append(p.gen_encfunc())
            if p.need_free:
                impl.append(c.blank())
                impl.append(p.gen_freefunc())
    hdr.append(c.blank())
    impl.append(c.blank())
    impl.append(gen_toclient_decode(org_packets))
    impl.append(c.blank())

    fp = open(hdr.path, 'w+')
    fp.write(str(hdr))
    fp.close()
    fp = open(impl.path, 'w+')
    fp.write(str(impl))
    fp.close()
