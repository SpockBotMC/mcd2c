# Midway upon the journey of our life
# I found myself within a forest dark,
# For the straight-forward pathway had been lost.

import cfile as c

# General ToDo:
#   ! cfile needs better pointer support
#   ! cfile's fcall is a constant source of bugs because of the return type
#     argument being where most cfile classes put their "elems" argument, and
#     the "arguments" parameter being optional
#   ! Division of concerns between cfile variables and mcd2c types is bad
#     you can easily str()-ify cfile variables, but not mcd2c types
#   ! Switched strings leak memory if a walk fails, need a goto failure mode

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
        return c.statement(
            c.assign(ret, c.fcall(f'enc_{self.postfix}', (dest, src)))
        )

    def dec_line(self, ret, dest, src):
        return c.statement(c.assign(ret, c.fcall(
            f'dec_{self.postfix}', 'char *', (f'&{dest.name}', src.name)
        )))

    def __eq__(self, value):
        return self.typename == value.typename

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.internal.name = name
        self._name = name

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
    def size_line(self, ret, field):
        return c.statement(
            c.addeq(ret, c.fcall(f'size_{self.postfix}', (field,)))
        )

    def walk_line(self, ret, src, max_len):
        assign = c.wrap(c.assign(
            ret, c.fcall(f'walk_{self.postfix}', 'int', (src, max_len))
        ))
        return c.inlineif(c.lth(assign, 0), c.returnval(-1))

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

@mc_data_name('restBuffer')
class mc_restbuffer(complex_type):
    typename = 'mc_buffer'
    postfix = 'buffer'

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_restbuffer dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    def free_line(self, field):
        pass

# Types which require some level of memory management
class memory_type(complex_type):
    def dec_line(self, ret, dest, src):
        assign = c.wrap(c.assign(
            ret,
            c.fcall(
                f'dec_{self.postfix}', 'char *', (f'&{dest.name}', src.name)
            )
        ), True)
        return c.inlineif(assign, c.returnval('NULL'))

    def walkdec_line(self, ret, dest, src):
        assign = c.wrap(c.assign(
            ret,
            c.fcall(
                f'dec_{self.postfix}', 'char *', (f'&{dest.name}', src.name)
            )
        ), True)
        return c.inlineif(assign, c.returnval(-1))

    def free_line(self, field):
        return c.statement(
            c.fcall(f'free_{self.postfix}', 'void', (field.name,))
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
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_buffer dec_line unimplemented')

    def walk_line(self, ret, src, max_len, size):
        seq = c.sequence()
        lenvar = c.variable(
            f'{self.name}_len', self.ln.typename
        )
        if isinstance(self.ln, numeric_type):
            seq.append(c.inlineif(
                c.lth(max_len, self.ln.size), c.returnval(-1))
            )
            seq.append(c.statement(c.addeq(size, self.ln.size)))
            seq.append(c.statement(c.subeq(max_len, self.ln.size)))
        else:
            seq.append(self.ln.walk_line(ret, src, max_len))
            seq.append(c.statement(c.addeq(size, ret)))
            seq.append(c.statement(c.subeq(max_len, ret)))
        seq.append(c.statement(lenvar.decl))
        seq.append(self.ln.dec_line(src, lenvar, src))
        seq.append(c.inlineif(c.lth(max_len, lenvar), c.returnval(-1)))
        seq.append(c.statement(c.addeq(size, lenvar)))
        seq.append(c.statement(c.addeq(src, lenvar)))
        seq.append(c.statement(c.subeq(max_len, lenvar)))
        return seq


    def free_line(self, field):
        pass

@mc_data_name('array')
class mc_array(custom_type, memory_type):
    def __init__(self, name, data, parent):
        super().__init__(name, data, parent)
        self.children = []
        if 'countType' in data:
            self.self_contained = True
            self.external_count = None
            self.count = get_type(data['countType'], 'count', self)
            self.children.append(self.count)
            self.base = get_type(data['type'], '*base', self)
        else:
            self.self_contained = False
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
            return c.linesequence((c.struct(elems = (
                self.count.struct_line(),
                self.base.struct_line()
            )), c.statement(self.name)))
        return self.base.struct_line()

    def enc_line(self, ret, dest, src):
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_array dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    def walk_line(self, ret, src, max_len, size):
        seq = c.sequence()
        # Hacking around cfile's lack of pointer support
        name = self.base.name[1:]
        if self.self_contained:
            count_var = c.variable(
                f'{name}_count', self.count.typename
            )
            if isinstance(self.count, numeric_type):
                seq.append(c.inlineif(
                    c.lth(max_len, self.count.size), c.returnval(-1))
                )
                seq.append(c.statement(c.addeq(size, self.count.size)))
                seq.append(c.statement(c.subeq(max_len, self.count.size)))
            else:
                seq.append(self.count.walk_line(ret, src, max_len))
                seq.append(c.statement(c.addeq(size, ret)))
                seq.append(c.statement(c.subeq(max_len, ret)))
            seq.append(c.statement(count_var.decl))
            seq.append(self.count.dec_line(src, count_var, src))
        else:
            count_var = self.external_count.internal
        if hasattr(self.base, 'size') and not self.base.size is None:
            seq.append(c.inlineif(
                c.lth(max_len, c.mulop(count_var, self.base.size)),
                c.returnval(-1)
            ))
            seq.append(c.statement(c.addeq(
                size, c.mulop(count_var, self.base.size)
            )))
            seq.append(c.statement(c.addeq(
                src, c.mulop(count_var, self.base.size)
            )))
            seq.append(c.statement(c.subeq(
                max_len, c.mulop(count_var, self.base.size)
            )))
        else:
            depth = get_depth(self)
            loopvar = c.variable(f'i_{depth}', 'size_t')
            if isinstance(self.base, custom_type):
                forelems = [self.base.walk_line(ret, src, max_len, size)]
            else:
                forelems = [self.base.walk_line(ret, src, max_len)]
                forelems.append(c.statement(c.addeq(size, ret)))
                forelems.append(c.statement(c.addeq(src, ret)))
                forelems.append(c.statement(c.subeq(max_len, ret)))
            seq.append(c.forloop(
                c.assign(loopvar.decl, 0),
                c.lth(loopvar, count_var),
                c.incop(loopvar, False),
                forelems
            ))

        return seq

    def free_line(self, field):
        pass

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
def group_numerics(fields, position):
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
            _, self.size = group_numerics(self.fields, 0)

    def __eq__(self, value):
        if not super().__eq__(value) or len(self.fields) != len(value.fields):
            return False
        return all([i == j for i, j in zip(self.fields, value.fields)])

    def struct_line(self):
        struct_fields = [f.struct_line() for f in self.fields]
        return c.linesequence((
            c.struct(elems = struct_fields),
            c.statement(self.name)
        ))

    def enc_line(self, ret, dest, src):
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_container dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    def walk_line(self, ret, src, max_len, size):
        seq = c.sequence()
        to_free = []
        position = 0
        endpos = len(self.fields)
        while(position < endpos):
            position, total = group_numerics(self.fields, position)
            if total:
                seq.append(c.inlineif(
                    c.lth(max_len, total), c.returnval(-1)
                ))
                seq.append(c.statement(c.addeq(size, total)))
                seq.append(c.statement(c.addeq(src, total)))
                seq.append(c.statement(c.subeq(max_len, total)))
            if position < endpos:
                field = self.fields[position]
                position += 1
                if field.switched:
                    #ToDo: Consider giving types a walk_switched method instead
                    # of this madness
                    seq.append(c.statement(field.internal.decl))
                    if isinstance(field, numeric_type):
                        seq.append(c.inlineif(
                            c.lth(max_len, field.size), c.returnval(-1)
                        ))
                        seq.append(c.statement(c.addeq(size, field.size)))
                        seq.append(c.statement(c.subeq(max_len, field.size)))
                    else:
                        seq.append(field.walk_line(ret, src, max_len))
                        seq.append(c.statement(c.addeq(size, ret)))
                        seq.append(c.statement(c.subeq(max_len, ret)))
                    if isinstance(field, memory_type):
                        seq.append(field.walkdec_line(src, field, src))
                        to_free.append(field)
                    else:
                        seq.append(field.dec_line(src, field, src))
                elif isinstance(field, custom_type):
                    seq.append(field.walk_line(ret, src, max_len, size))
                else:
                    seq.append(field.walk_line(ret, src, max_len))
                    seq.append(c.statement(c.addeq(size, ret)))
                    seq.append(c.statement(c.addeq(src, ret)))
                    seq.append(c.statement(c.subeq(max_len, ret)))
        for field in to_free:
            seq.append(field.free_line(field))
        return seq

    def free_line(self, field):
        pass

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
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_option dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    def walk_line(self, ret, src, max_len, size):
        func_lines = []
        func_lines.append(c.inlineif(
            c.lth(max_len, self.opt.size), c.returnval(-1)
        ))
        optvar = c.variable(f'{self.name}_opt', self.opt.typename)
        func_lines.append(c.statement(optvar.decl))
        func_lines.append(self.opt.dec_line(src, optvar, src))
        func_lines.append(c.statement(c.addeq(size, self.opt.size)))
        func_lines.append(c.statement(c.subeq(max_len, self.opt.size)))
        ifelems = []
        if isinstance(self.val, custom_type):
            ifelems.append(self.val.walk_line(ret, src, max_len, size))
        elif isinstance(self.val, numeric_type):
            ifelems.append(c.inlineif(
                c.lth(max_len, self.val.size), c.returnval(-1)
            ))
            ifelems.append(c.statement(c.addeq(size, self.val.size)))
            ifelems.append(c.statement(c.addeq(src, self.val.size)))
            ifelems.append(c.statement(c.subeq(max_len, self.val.size)))
        else:
            ifelems = [self.val.walk_line(ret, src, max_len)]
            ifelems.append(c.statement(c.addeq(size, ret)))
            ifelems.append(c.statement(c.addeq(src, ret)))
            ifelems.append(c.statement(c.subeq(max_len, ret)))
        func_lines.append(c.ifcond(optvar, ifelems))
        return c.sequence(func_lines)

    def free_line(self, field):
        pass

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

def generic_walk_func(app, field, ret, src, max_len, size):
    if isinstance(field, numeric_type):
        app.append(c.statement(c.addeq(size, field.size)))
        app.append(c.statement(c.addeq(src, field.size)))
        app.append(c.statement(c.subeq(max_len, field.size)))
    else:
        if isinstance(field, custom_type):
            app.append(field.walk_line(ret, src, max_len, size))
        else:
            app.append(field.walk_line(ret, src, max_len))
            app.append(c.statement(c.addeq(size, ret)))
            app.append(c.statement(c.addeq(src, ret)))
            app.append(c.statement(c.subeq(max_len, ret)))


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
            self.optional_case = next(iter(self.map))
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
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_switch dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    def walk_line(self, ret, src, max_len, size):
        if not self.string_switch and self.isbool and self.optional:
            elems = []
            generic_walk_func(elems, self.fields[0], ret, src, max_len, size)
            if self.optional_case:
                return c.ifcond(self.cp_short, elems)
            else:
                return c.wrap(c.ifcond(self.cp_short, elems), True)

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
                        generic_walk_func(cf, field, ret, src, max_len, size)
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
                        df, self.default_typ, ret, src, max_len, size
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
                    'sdscmp', 'int', (f'\'{caseval}\'', self.cp_short)
                ), True))
                first = False
            else:
                cf = c.elifcond(c.wrap(c.fcall(
                    'sdscmp', 'int', (f'\'{caseval}\'', self.cp_short)
                ), True))
            if isinstance(field, void_type):
                cf.append(c.linecomment('void condition'))
            else:
                generic_walk_func(cf, field, ret, src, max_len, size)
            sw.append(cf)
        if self.has_default:
            df = c.defaultcase()
            generic_walk_func(
                df, self.default_typ, ret, src, max_len, size
            )
            sw.append(df)
        return sw




    def free_line(self, field):
        pass


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
        for field in data:
            shift = total
            total += field['size']
            if field['name'] in ('_unused', 'unused'):
                continue
            self.field_sizes[field['name']] = field['size']
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
        struct_fields = [f.struct_line() for f in self.fields]
        return c.linesequence((
            c.struct(elems = struct_fields),
            c.statement(self.name)
        ))

    def enc_line(self, ret, dest, src):
        pass

    def dec_line(self, ret, dest, src):
        return c.linecomment('mc_bitfield dec_line unimplemented')

    def size_line(self, ret, field):
        pass

    # Only called if one or more fields are switched on
    def walk_line(self, ret, src, max_len, size):
        seq = c.sequence()
        seq.append(c.inlineif(c.lth(max_len, self.size), c.returnval(-1)))
        seq.append(c.statement(self.storage.internal.decl))
        seq.append(c.statement(c.addeq(size, self.size)))
        seq.append(c.statement(c.subeq(max_len, self.size)))
        seq.append(self.storage.dec_line(src, self.storage, src))
        for idx, field in enumerate(self.fields):
            if not field.switched:
                continue
            mask, shift = self.mask_shift[idx]
            # I could wrap this in three more c.[func] calls or write one
            # little f-string, I go with f-string
            seq.append(c.statement(c.assign(
                field.internal.decl, f'({self.storage.name}>>{shift})&{mask}'
            )))
        return seq


    def free_line(self, field):
        pass

@mc_data_name('particleData')
class mc_particledata(custom_type, memory_type):
    typename = 'mc_particle'
    postfix = 'particledata'

    def dec_line(self, ret, dest, src, part_type):
        return c.statement(c.assign(
            ret, c.fcall(
                f'dec_{self.postfix}', 'char *', (dest, src, part_type)
            )
        ))

    def walk_line(self, ret, src, max_len, size):
        return c.linecomment('particledata not yet implemented')

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
                print(f'Anonymous field in: {full_name}')
            pckt.append(get_type(field['type'], fname, pckt))
        # ToDo: This is a stupid hack, should be replaced my instantiating
        # fields in init by passing something like (typ, fname) tuples instead
        # instead of instantiated fields.
        return pckt

    def gen_struct(self):
        struct_fields = [f.struct_line() for f in self.fields]
        return c.typedef(c.struct(elems = struct_fields), self.full_name)

    def gen_function_defs(self):
        src = c.variabledecl('*source', 'char')
        dest = c.variabledecl('*dest', 'char')
        pak = c.variabledecl('packet', self.full_name)
        max_len = c.variabledecl('max_len', 'size_t')
        pak_src = c.variabledecl('source', self.full_name)
        pak_dest = c.variabledecl('*dest', self.full_name)

        s = c.sequence([
            c.statement(c.fdecl(
                f'walk_{self.full_name}', 'int', (src, max_len)
            )),
            c.statement(c.fdecl(f'size_{self.full_name}', 'size_t', (pak,))),
            c.statement(c.fdecl(
                f'enc_{self.full_name}', 'char *', (dest, pak_src)
            )),
            c.statement(c.fdecl(
                f'dec_{self.full_name}', 'char *', (pak_dest, src)
            )),
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
            position, total = group_numerics(self.fields, 0)
            return c.linesequence((c.fdecl(
                f'walk_{self.full_name}', 'int', (src.decl, max_len.decl)
            ), c.block((
                c.inlineif(c.lth(max_len, total), c.returnval(-1)),
                c.returnval(total)))
            ))

        ret = c.variable('ret', 'int')
        size = c.variable('size', 'int')
        #cfile lacks the capability to group variables declarations
        blk = c.block(elems=[c.statement(f'{ret.decl}, {c.assign(size, 0)}')])
        to_free = []
        position = 0
        endpos = len(self.fields)
        while(position < endpos):
            position, total = group_numerics(self.fields, position)
            if total:
                blk.append(c.inlineif(
                    c.lth(max_len, total), c.returnval(-1)
                ))
                if position < endpos:
                    blk.append(c.statement(c.addeq(size, total)))
                    blk.append(c.statement(c.addeq(src, total)))
                    blk.append(c.statement(c.subeq(max_len, total)))
                else:
                    del blk[-3:-1]
                    blk.append(c.returnval(c.addop(size, total)))
            if position < endpos:
                field = self.fields[position]
                position += 1
                if field.switched:
                    blk.append(c.statement(field.internal.decl))
                    if isinstance(field, numeric_type):
                        blk.append(c.inlineif(
                            c.lth(max_len, field.size), c.returnval(-1)
                        ))
                        blk.append(c.statement(c.addeq(size, field.size)))
                        blk.append(c.statement(c.subeq(max_len, field.size)))
                    else:
                        blk.append(field.walk_line(ret, src, max_len))
                        blk.append(c.statement(c.addeq(size, ret)))
                        blk.append(c.statement(c.subeq(max_len, ret)))
                    if isinstance(field, memory_type):
                        blk.append(field.walkdec_line(src, field, src))
                        to_free.append(field)
                    else:
                        blk.append(field.dec_line(src, field, src))
                elif isinstance(field, custom_type):
                    blk.append(field.walk_line(ret, src, max_len, size))
                    if position >= endpos:
                        blk.append(c.returnval(size))
                else:
                    blk.append(field.walk_line(ret, src, max_len))
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
        pak = c.variabledecl('packet', self.full_name)
        if not self.complex:
            position, total = group_numerics(self.fields, 0)
            return c.linesequence((
                c.fdecl(f'size_{self.full_name}', 'size_t', (pak,)),
                c.block((c.returnval(total),))
            ))
        blk = c.block([c.linecomment('Complex sizefunc unimplemented')])
        blk.append(c.returnval(0))
        return c.linesequence((
            c.fdecl(f'size_{self.full_name}', 'size_t', (pak,)), blk
        ))

    def gen_decfunc(self):
        dest = c.variabledecl('packet', self.full_name)
        destptr = c.variabledecl('*packet', self.full_name)
        src = c.variable('source', 'char *')
        blk = c.block()
        for field in self.fields:
            if not isinstance(field, custom_type) and not isinstance(field, memory_type):
                v = c.variable(f'{dest.name}->{field.name}', field.typename)
                blk.append(field.dec_line(src, v, src))
            else:
                blk.append(c.linecomment('custom_type unimplemented'))
        blk.append(c.returnval(src))
        return c.linesequence((
            c.fdecl(f'dec_{self.full_name}', 'char *', (destptr, src.decl)), blk
        ))

    def gen_encfunc(self):
        pass

    def gen_freefunc(self):
        pass


import minecraft_data

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
    impl.append(c.include(hdr.path))
    impl.append(c.blank())

    packets = []
    for state in "handshaking", "login", "status", "play":
        for direction in "toClient", "toServer":
            packet_map = data[state][direction]['types']['packet'][1][1]['type'][1]['fields']
            for name, id in packet_map.items():
                pd = data[state][direction]['types'][id]
                packets.append(packet.from_proto(state, direction, name, pd))

    for p in packets:
        if(p.fields):
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

    fp = open(hdr.path, 'w+')
    fp.write(str(hdr))
    fp.close()
    fp = open(impl.path, 'w+')
    fp.write(str(impl))
    fp.close()

if __name__ == '__main__':
    run('1.14.4')
